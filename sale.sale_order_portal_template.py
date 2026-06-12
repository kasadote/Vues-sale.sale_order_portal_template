<data name="Sales Order" inherit_id="portal.portal_sidebar" primary="True">
        <xpath expr="//div[hasclass('o_portal_sidebar')]" position="inside">
            <t t-set="o_portal_fullwidth_alert" groups="sales_team.group_sale_salesman">
                <!-- Uses backend_url provided in rendering values -->
                <t t-call="portal.portal_back_in_edit_mode"/>
            </t>

            <div class="row o_portal_sale_sidebar">
                <!-- Sidebar -->
                <t t-call="portal.portal_record_sidebar" id="sale_order_portal_sidebar">
                    <t t-set="classes" t-value="'col-lg-4 col-xxl-3 d-print-none'"/>

                    <t t-set="title">
                        <h2 t-field="sale_order.amount_total" data-id="total_amount" class="mb-0 text-break"/>
                    </t>
                    <t t-set="entries">
                        <div class="d-flex flex-column gap-4 mt-3">
                            <div class="d-flex flex-column gap-2" id="sale_order_sidebar_button">
                                <a t-if="sale_order._has_to_be_signed()" role="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#modalaccept" href="#">
                                    <i class="fa fa-check"/><t t-if="sale_order._has_to_be_paid()"> Signer &amp; Payer</t><t t-else=""> Accepter &amp; Signer</t>
                                </a>
                                <a t-elif="sale_order._has_to_be_paid()" role="button" id="o_sale_portal_paynow" data-bs-toggle="modal" data-bs-target="#modalaccept" href="#" t-att-class="'%s' % ('btn btn-light' if sale_order.transaction_ids else 'btn btn-primary')">
                                    <i class="fa fa-check"/> <t t-if="not sale_order.signature">Accepter &amp; Payer</t><t t-else="">Payer maintenant</t>
                                </a>
                                <div class="o_download_pdf d-flex gap-2 flex-lg-column flex-xl-row flex-wrap">
                                    <a class="btn btn-light o_print_btn o_portal_invoice_print flex-grow-1" t-att-href="sale_order.get_portal_url(report_type='pdf')" id="print_invoice_report" title="Voir les détails" role="button" target="_blank"><i class="fa fa-print me-1"/> Voir les détails</a>
                                </div>
                            </div>

                            <div class="navspy flex-grow-1 ps-0" t-ignore="true" role="complementary">
                                <ul class="nav flex-column bs-sidenav"/>
                            </div>

                            <t t-if="not sale_order.is_expired and sale_order.state in ['draft', 'sent']">
                                <div t-if="sale_order.amount_undiscounted - sale_order.amount_untaxed &gt; 0.01" class="list-group-item flex-grow-1" name="sale_order_advantage">
                                    <small class=""><b class="text-muted">Votre rabais</b></small>
                                    <small>
                                        <b t-field="sale_order.amount_undiscounted" t-options="{&quot;widget&quot;: &quot;monetary&quot;, &quot;display_currency&quot;: sale_order.currency_id}" style="text-decoration: line-through" class="d-block mt-1" data-id="amount_undiscounted"/>
                                    </small>
                                    <t t-if="sale_order.amount_untaxed == sale_order.amount_total">
                                        <h4 t-field="sale_order.amount_total" class="text-success" data-id="total_amount"/>
                                    </t>
                                    <t t-else="">
                                        <h4 t-field="sale_order.amount_untaxed" class="text-success mb-0" data-id="total_untaxed"/>
                                        <small>(<span t-field="sale_order.amount_total" data-id="total_amount"/> Toutes taxes comprises)</small>
                                    </t>
                                </div>
                            </t>

                            <div t-if="sale_order.user_id">
                                <h6><small class="text-muted">Votre contact</small></h6>
                                <t t-call="portal.portal_my_contact">
                                    <t t-set="_contactAvatar" t-value="image_data_uri(sale_order.user_id.avatar_128)"/>
                                    <t t-set="_contactName" t-value="sale_order.user_id.name"/>
                                    <t t-set="_contactLink" t-value="True"/>
                                </t>
                            </div>
                        </div>
                    </t>
                </t>

                <!-- Page content -->
                <div id="quote_content" class="col-12 col-lg-8 col-xxl-9 mt-5 mt-lg-0">

                    <!-- modal relative to the actions sign and pay -->
                    <div role="dialog" class="modal fade" id="modalaccept" name="sale_order_modal_sign_and_pay">
                        <div class="modal-dialog" t-if="sale_order._has_to_be_signed()">
                            <form id="accept" method="POST" t-att-data-order-id="sale_order.id" t-att-data-token="sale_order.access_token" class="js_accept_json modal-content js_website_submit_form">
                                <input type="hidden" name="csrf_token" t-att-value="request.csrf_token()"/>
                                <header class="modal-header">
                                    <h4 class="modal-title">Confirmer la commande</h4>
                                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fermer"/>
                                </header>
                                <main class="modal-body" id="sign-dialog">
                                    <span>
                                        En signant, vous confirmez l'acceptation au nom de
                                        <b t-field="sale_order.partner_id.commercial_partner_id"/>
                                        pour le <b data-id="total_amount" t-field="sale_order.amount_total"/> devis.
                                    </span>
                                    <b t-if="sale_order.payment_term_id" t-field="sale_order.payment_term_id.note"/>
                                    <t t-call="portal.signature_form">
                                        <t t-set="call_url" t-value="sale_order.get_portal_url(suffix='/accept')"/>
                                        <t t-set="default_name" t-value="sale_order.partner_id.name or sale_order.partner_id.commercial_partner_id.name"/>
                                    </t>
                                </main>
                            </form>
                        </div>

                        <div class="modal-dialog" t-if="not sale_order._has_to_be_signed() and sale_order._has_to_be_paid()" name="sale_order_modal_validate">
                            <div class="modal-content">
                                <header class="modal-header">
                                    <h4 class="modal-title">Confirmer la commande</h4>
                                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fermer"/>
                                </header>
                                <main class="modal-body" id="sign-dialog">
                                    <t t-set="prepayment_amount" t-value="sale_order._get_prepayment_required_amount()"/>
                                    <t t-set="prepayment_available" t-value="sale_order.prepayment_percent and sale_order.prepayment_percent != 1.0"/>
                                    <!-- Display choices only if a pre payment can confirm the order. -->
                                    <div t-if="prepayment_available" id="o_sale_portal_prepayment_buttons" class="d-flex btn-group mb-3" role="group">
                                        <button name="o_sale_portal_amount_prepayment_button" class="btn btn-light active">
                                            Acompte <br/>
                                            <span t-esc="prepayment_amount" class="fw-bold" t-options="{'widget': 'monetary', 'display_currency': sale_order.currency_id}"/>
                                        </button>
                                        <button name="o_sale_portal_amount_total_button" class="btn btn-light">
                                            Montant intégral <br/>
                                            <span class="fw-bold" t-field="sale_order.amount_total"/>
                                        </button>
                                    </div>
                                    <div class="mb-3">
                                        <!-- The widget associated with this modal will hide and show divs in function of the amount selected. -->
                                        <span t-if="prepayment_available">
                                            <span id="o_sale_portal_use_amount_prepayment">
                                                En payant cet <u>acompte</u> de
                                                <span t-esc="prepayment_amount" t-options="{'widget': 'monetary', 'display_currency': sale_order.currency_id}" class="fw-bold"/>
                                                (<b t-esc="sale_order.prepayment_percent * 100"/>%),
                                            </span>
                                            <span id="o_sale_portal_use_amount_total">
                                                En payant,
                                            </span>
                                        </span>
                                        <span t-else="">
                                            En payant,
                                        </span>
                                        vous confirmez l'acceptation au nom de <b t-field="sale_order.partner_id.commercial_partner_id"/>
                                        pour le <b data-id="total_amount" t-field="sale_order.amount_total"/> devis.
                                        <b t-if="sale_order.payment_term_id" t-field="sale_order.payment_term_id.note" class="o_sale_payment_terms"/>
                                    </div>
                                    <div t-if="company_mismatch">
                                        <t t-call="payment.company_mismatch_warning"/>
                                    </div>
                                    <div t-elif="not sale_order._has_to_be_paid()" class="alert alert-danger">
                                        La commande ne requiert pas de paiement de la part du client.
                                    </div>
                                    <div t-else="" id="payment_method" class="text-start mt-0">
                                        <t t-call="payment.form">
                                            <!-- Inject the order ID to allow Stripe to check if tokenization is required. -->
                                            <t t-set="sale_order_id" t-value="sale_order.id"/>
                                        </t>
                                    </div>
                                </main>
                            </div>
                        </div>
                    </div>

                    <!-- modal relative to the action reject -->
                    <div role="dialog" class="modal fade" id="modaldecline">
                        <div class="modal-dialog">
                            <form id="decline" method="POST" t-attf-action="/my/orders/#{sale_order.id}/decline?access_token=#{sale_order.access_token}" class="modal-content">
                                <input type="hidden" name="csrf_token" t-att-value="request.csrf_token()"/>
                                <header class="modal-header">
                                    <h4 class="modal-title">Rejeter ce devis</h4>
                                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fermer"/>
                                </header>
                                <main class="modal-body">
                                    <p>
                                        Dites nous pourquoi vous refusez ce devis afin de nous aider à améliorer nos services.
                                    </p>
                                    <textarea rows="4" name="decline_message" required="" placeholder="Votre feedback..." class="form-control"/>
                                </main>
                                <footer class="modal-footer">
                                    <button type="submit" t-att-id="sale_order.id" class="btn btn-danger">
                                        <i class="fa fa-times"/> Rejeter
                                    </button>
                                    <button type="button" class="btn btn-primary" data-bs-dismiss="modal">
                                        Annuler
                                    </button>
                                </footer>
                            </form>
                        </div>
                    </div>

                    <!-- status messages -->
                    <div t-if="message == 'sign_ok'" class="alert alert-success alert-dismissible d-print-none" role="status">
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Fermer"/>
                        <strong>Merci !</strong><br/>
                        <t t-if="message == 'sign_ok' and sale_order.state == 'sale'">
                            Votre commande a été confirmée.
                        </t>
                        <t t-elif="message == 'sign_ok' and sale_order._has_to_be_paid()">
                            Votre commande a été signée mais doit toujours être payée afin de pouvoir être validée.
                        </t>
                        <t t-else="">Votre commande a été signée.</t>
                    </div>

                    <div t-if="message == 'cant_reject'" class="alert alert-danger alert-dismissible d-print-none" role="alert">
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Fermer"/>
                        Votre commande n'est pas en état d'être rejetée.
                    </div>

                    <t t-if="sale_order.get_portal_last_transaction()">
                        <t t-call="payment.state_header">
                            <t t-set="tx" t-value="sale_order.get_portal_last_transaction()"/>
                        </t>
                    </t>

                    <div t-if="sale_order.state == 'cancel'" class="alert alert-danger alert-dismissible d-print-none" role="alert">
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="fermer"/>
                        <strong>Ce devis a été annulé.</strong> <a role="button" href="#discussion"><i class="fa fa-comment"/> Contactez-nous pour un nouveau devis.</a>
                    </div>

                    <div t-if="sale_order.is_expired" class="alert alert-warning alert-dismissible d-print-none" role="alert">
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="fermer"/>
                        <strong>Cette offre a expiré !</strong> <a role="button" href="#discussion"><i class="fa fa-comment"/> Contactez-nous pour un nouveau devis.</a>
                    </div>

                    <!-- main content -->
                    <div t-attf-class="#{'pb-5' if report_type == 'html' else ''}" id="portal_sale_content">
                        <div t-call="#{sale_order._get_name_portal_content_view()}"/>
                    </div>

                    <!-- bottom actions -->
                    <div t-if="sale_order._has_to_be_signed() or sale_order._has_to_be_paid()" class="d-flex justify-content-center gap-1 d-print-none" name="sale_order_actions">

                        <t t-if="sale_order._has_to_be_signed()">
                            <div class="col-sm-auto mt8">
                                <a role="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#modalaccept" href="#"><i class="fa fa-check"/><t t-if="sale_order._has_to_be_paid()"> Signer &amp; Payer</t><t t-else=""> Accepter &amp; Signer</t></a>
                            </div>
                            <div class="col-sm-auto mt8">
                                <a role="button" class="btn btn-light" href="#discussion"><i class="fa fa-comment"/> Commentaires</a>
                            </div>
                            <div class="col-sm-auto mt8">
                                <a role="button" class="btn btn-danger" data-bs-toggle="modal" data-bs-target="#modaldecline" href="#"> <i class="fa fa-times"/> Rejeter</a>
                            </div>
                        </t>
                        <div t-elif="sale_order._has_to_be_paid()" class="col-sm-auto mt8">
                            <a role="button" data-bs-toggle="modal" data-bs-target="#modalaccept" href="#" t-att-class="'%s' % ('btn btn-light' if sale_order.transaction_ids else 'btn btn-primary')">
                                <i class="fa fa-check"/> <t t-if="not sale_order.signature">Accepter &amp; Payer</t><t t-else="">Payer maintenant</t>
                            </a>
                        </div>
                    </div>

                    <!-- chatter -->
                    <hr/>
                    <div id="sale_order_communication">
                        <h3>Historique de la communication</h3>
                        <t t-call="portal.message_thread"/>
                    </div>
                </div><!-- // #quote_content -->
            </div>
        </xpath>
    <xpath expr="." position="attributes"><attribute name="t-name">sale.sale_order_portal_template</attribute></xpath></data>
