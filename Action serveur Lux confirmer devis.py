# =========================
# OUTILS
# =========================
def _get_free_qty(product, location):
    if location:
        return product.with_context(location=location.id).free_qty
    return product.free_qty


def _add_need(needs_map, component, qty_needed, sold_product_label):
    if component.id not in needs_map:
        needs_map[component.id] = {
            'product': component,
            'qty': 0.0,
            'parents': {}
        }

    needs_map[component.id]['qty'] += qty_needed
    parents = needs_map[component.id]['parents']
    parents[sold_product_label] = parents.get(sold_product_label, 0.0) + qty_needed


def _bom_for_product(prod, company):
    bom = env['mrp.bom'].search([
        ('product_id', '=', prod.id),
        '|', ('company_id', '=', False), ('company_id', '=', company.id)
    ], limit=1)
    if bom:
        return bom

    bom = env['mrp.bom'].search([
        ('product_tmpl_id', '=', prod.product_tmpl_id.id),
        ('product_id', '=', False),
        '|', ('company_id', '=', False), ('company_id', '=', company.id)
    ], limit=1)
    return bom


def _append_option(options, attribute_name, value_name):
    options.append({
        'attribute': attribute_name or '',
        'value': value_name or '',
    })


def _get_line_selected_options(line):
    options = []
    value_ids = []

    for ptav in line.product_template_attribute_value_ids:
        attribute_name = ''
        value_name = ''

        if ptav.attribute_line_id and ptav.attribute_line_id.attribute_id:
            attribute_name = ptav.attribute_line_id.attribute_id.name or ''
        elif ptav.product_attribute_value_id and ptav.product_attribute_value_id.attribute_id:
            attribute_name = ptav.product_attribute_value_id.attribute_id.name or ''

        if ptav.product_attribute_value_id:
            value_name = ptav.product_attribute_value_id.name or ''
        else:
            value_name = ptav.name or ''

        _append_option(options, attribute_name, value_name)
        value_ids.append(ptav.id)

    for pav in line.product_no_variant_attribute_value_ids:
        attribute_name = ''
        value_name = ''

        if pav.attribute_id:
            attribute_name = pav.attribute_id.name or ''
        value_name = pav.name or ''

        _append_option(options, attribute_name, value_name)
        value_ids.append(pav.id)

    return {
        'options': options,
        'value_ids': value_ids,
    }


def _get_bom_components_for_line(line, company):
    product = line.product_id
    bom = _bom_for_product(product, company)

    line_option_data = _get_line_selected_options(line)
    selected_value_ids = line_option_data['value_ids']

    if not bom:
        return {
            'bom': False,
            'components': [],
        }

    components = []

    for bom_line in bom.bom_line_ids:
        include_line = False

        if not bom_line.bom_product_template_attribute_value_ids:
            include_line = True
        else:
            include_line = False
            for value in bom_line.bom_product_template_attribute_value_ids:
                if value.id in selected_value_ids:
                    include_line = True
                    break

        if include_line and bom_line.product_id:
            components.append({
                'product': bom_line.product_id,
                'qty': bom_line.product_qty,
                'uom': bom_line.product_uom_id,
            })

    return {
        'bom': bom,
        'components': components,
    }


# =========================
# PASSAGE 1 : VERIFICATION STOCK
# =========================
for order in records:
    if order.state not in ['draft', 'sent']:
        continue

    warehouse = order.warehouse_id
    location = warehouse.lot_stock_id if warehouse else False

    needs_map = {}

    for line in order.order_line:
        product = line.product_id

        if not product:
            continue

        if product.type not in ['product', 'consu']:
            continue

        bom_data = _get_bom_components_for_line(line, order.company_id)
        bom = bom_data['bom']
        components = bom_data['components']

        qty_line_product_uom = line.product_uom._compute_quantity(
            line.product_uom_qty,
            product.uom_id
        )

        if bom and components:
            bom_qty_in_product_uom = bom.product_uom_id._compute_quantity(
                bom.product_qty,
                product.uom_id
            )

            if not bom_qty_in_product_uom:
                bom_qty_in_product_uom = 1.0

            factor = qty_line_product_uom / bom_qty_in_product_uom

            for comp in components:
                component = comp['product']
                comp_qty_bom = comp['qty']
                comp_uom = comp['uom']

                if not component:
                    continue

                if component.type not in ['product', 'consu']:
                    continue

                if comp_uom:
                    component_qty = comp_uom._compute_quantity(
                        comp_qty_bom,
                        component.uom_id
                    ) * factor
                else:
                    component_qty = comp_qty_bom * factor

                _add_need(
                    needs_map=needs_map,
                    component=component,
                    qty_needed=component_qty,
                    sold_product_label=product.display_name
                )

        else:
            _add_need(
                needs_map=needs_map,
                component=product,
                qty_needed=qty_line_product_uom,
                sold_product_label=product.display_name
            )

    insuff = []

    for vals in needs_map.values():
        component = vals['product']
        qty_demandee = vals['qty']
        stock_libre = _get_free_qty(component, location)

        if qty_demandee > stock_libre:
            parents = vals['parents']
            detail_parents = []

            for parent_name, parent_qty in parents.items():
                if parent_name != component.display_name:
                    detail_parents.append(
                        "  Issue de : %s | besoin %.2f" % (parent_name, parent_qty)
                    )

            message = (
                "- %s\n"
                "  Demandé : %.2f | Disponible : %.2f"
                % (
                    component.display_name,
                    qty_demandee,
                    stock_libre,
                )
            )

            if detail_parents:
                message += "\n" + "\n".join(detail_parents)

            insuff.append(message)

    policy = order.x_studio_stock_exception_policy or 'block'

    if insuff and policy in ['partial', 'extended']:
        continue

    if insuff:
        raise UserError(
            "Confirmation bloquée.\n\n"
            "Certains articles / composants ne sont pas disponibles dans l'entrepôt %s :\n\n"
            % (warehouse.display_name if warehouse else "")
            + "\n\n".join(insuff)
            + "\n\nVeuillez proposer un remplacement ou aviser le client."
        )


# =========================
# PASSAGE 2 : GESTION CLIENT FINAL
# =========================
orders_to_confirm = env['sale.order']
standard_orders = env['sale.order']

for order in records:
    if order.state not in ['draft', 'sent']:
        continue

    partner = order.partner_id
    is_client_final = partner and partner.x_studio_client_final

    if not is_client_final:
        orders_to_confirm |= order
        standard_orders |= order
        continue

    # ── CLIENT FINAL : traitement spécial ──

    # 1) Identifier la société mère
    company = (
        partner.x_studio_societe_commande
        or partner.parent_id
        or partner.commercial_partner_id
    )

    if not company or company.id == partner.id:
        orders_to_confirm |= order
        standard_orders |= order
        continue

    # 2) Conserver les infos du devis original
    original_name = order.name or ''
    original_ref  = order.client_order_ref or ''

    # 3) Générer le PDF du devis ébéniste AVANT duplication
    pdf_content_ebeniste, _ = env['ir.actions.report']._render_qweb_pdf(
        'sale.report_saleorder',
        order.id
    )
    attachment_ebeniste = env['ir.attachment'].create({
        'name': 'Devis_%s.pdf' % original_name,
        'type': 'binary',
        'raw': pdf_content_ebeniste,
        'res_model': 'sale.order',
        'res_id': order.id,
        'mimetype': 'application/pdf',
    })

    # 4) Dupliquer le devis original
    # Note : x_studio_opportunit est automatiquement copié par la duplication
    new_order = order.copy()

    # 5) Référence du nouveau devis : Ref originale - Nom client ébéniste
    if original_ref:
        new_ref = "%s - %s" % (original_ref, partner.name)
    else:
        new_ref = "%s - %s" % (original_name, partner.name)

    new_order.write({
        'client_order_ref': new_ref,
        'partner_id': company.id,
        'pricelist_id': company.property_product_pricelist.id
            if company.property_product_pricelist else False,
    })

    # 6) Recalculer les prix selon la grille tarifaire de la société
    try:
        new_order.action_update_prices()
    except Exception:
        for line in new_order.order_line:
            line.write({'product_uom_qty': line.product_uom_qty})

    # 7) Lier les deux devis bidirectionnellement
    new_order.write({'x_studio_devis_origine_id': order.id})
    order.write({'x_studio_commande_lie_id': new_order.id})

    # 8) Mettre à jour le revenu prévu sur l'opportunité CRM
    if order.x_studio_opportunit:
        order.x_studio_opportunit.write({
            'expected_revenue': new_order.amount_untaxed,
        })

    # 9) Retirer les abonnés client final du nouveau devis
    for follower in new_order.message_partner_ids:
        if follower.x_studio_client_final:
            new_order.message_unsubscribe(partner_ids=[follower.id])

    # 10) Générer le PDF devis Cuisi-lam (prix PRO)
    pdf_content_cusilam, _ = env['ir.actions.report']._render_qweb_pdf(
        'sale.report_saleorder',
        new_order.id
    )
    attachment_cusilam = env['ir.attachment'].create({
        'name': 'Devis_%s.pdf' % (new_order.name or ''),
        'type': 'binary',
        'raw': pdf_content_cusilam,
        'res_model': 'sale.order',
        'res_id': new_order.id,
        'mimetype': 'application/pdf',
    })

    # 11) Générer le bon de livraison depuis devis Cuisi-lam
    pdf_content_bon_livraison, _ = env['ir.actions.report']._render_qweb_pdf(
        'sale.report_delivery_lux',
        new_order.id
    )
    attachment_bon_livraison = env['ir.attachment'].create({
        'name': 'BonLivraison_%s.pdf' % (new_order.name or ''),
        'type': 'binary',
        'raw': pdf_content_bon_livraison,
        'res_model': 'sale.order',
        'res_id': new_order.id,
        'mimetype': 'application/pdf',
    })

    # 12) Récupérer les templates
    template_cusilam = env['mail.template'].browse(199)
    template_ebeniste = env['mail.template'].browse(200)

    # 13) Rendre le corps et sujet via mail.render.mixin Odoo 18
    body_cusilam = env['mail.render.mixin']._render_template_qweb(
        template_cusilam.body_html, 'sale.order', [new_order.id]
    ).get(new_order.id, '') or ''

    subject_cusilam = env['mail.render.mixin']._render_template_inline_template(
        template_cusilam.subject, 'sale.order', [new_order.id]
    ).get(new_order.id, '') or ''

    body_ebeniste = env['mail.render.mixin']._render_template_qweb(
        template_ebeniste.body_html, 'sale.order', [order.id]
    ).get(order.id, '') or ''

    subject_ebeniste = env['mail.render.mixin']._render_template_inline_template(
        template_ebeniste.subject, 'sale.order', [order.id]
    ).get(order.id, '') or ''

    # 14) Envoyer mail Cuisi-lam avec les trois PDFs joints
    #     - PDF devis Cuisi-lam (prix PRO)
    #     - PDF bon de livraison depuis devis
    #     - PDF devis ébéniste (prix distributeur)
    new_order.message_post(
        body=body_cusilam,
        subject=subject_cusilam,
        message_type='email',
        subtype_xmlid='mail.mt_comment',
        partner_ids=[company.id],
        attachment_ids=[
            attachment_cusilam.id,
            attachment_bon_livraison.id,
            attachment_ebeniste.id,
        ],
        email_from=template_cusilam.email_from or env.user.email_formatted,
        email_layout_xmlid='mail.mail_notification_light',
    )

    # 15) Envoyer mail ébéniste avec son PDF joint
    order.message_post(
        body=body_ebeniste,
        subject=subject_ebeniste,
        message_type='email',
        subtype_xmlid='mail.mt_comment',
        partner_ids=[partner.id],
        attachment_ids=[attachment_ebeniste.id],
        email_from=template_ebeniste.email_from or env.user.email_formatted,
        email_layout_xmlid='mail.mail_notification_light',
    )

    # 16) Messages chatter sur les deux devis
    new_order.message_post(
        body=(
            '📋 Cette commande provient du devis client '
            '<a href="/web#id=%s&amp;model=sale.order&amp;view_type=form"><b>%s</b></a> '
            '(annulé suite à transformation).'
        ) % (order.id, original_name),
        body_is_html=True,
        message_type='comment',
        subtype_xmlid='mail.mt_note',
    )

    order.message_post(
        body=(
            '🔄 Nouveau devis commande généré : '
            '<a href="/web#id=%s&amp;model=sale.order&amp;view_type=form"><b>%s</b></a> '
            '(basculé vers la société %s).'
        ) % (new_order.id, new_order.name or '', company.display_name),
        body_is_html=True,
        message_type='comment',
        subtype_xmlid='mail.mt_note',
    )

    # 17) Annuler le devis original
    try:
        if order.state == 'sent':
            order.sudo().action_draft()
        order.sudo().action_cancel()
    except Exception:
        order.sudo().write({'state': 'cancel'})

    # 18) Le nouveau devis sera confirmé au passage 3
    orders_to_confirm |= new_order


# =========================
# PASSAGE 3 : CONFIRMATION
# =========================
if orders_to_confirm:
    orders_to_confirm.action_confirm()

# Envoi du template de confirmation pour les commandes standards
if standard_orders:
    template_confirm = env['mail.template'].browse(31)
    for so in standard_orders:
        composer = env['mail.compose.message'].with_context(
            default_model='sale.order',
            default_res_ids=so.ids,
            default_template_id=template_confirm.id,
            default_composition_mode='comment',
            mark_so_as_sent=True,
            force_send=True,
        ).create({})
        composer._action_send_mail()
