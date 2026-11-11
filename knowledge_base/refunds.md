# Refund and return handling

These policy passages are synthetic operational guidance for the Acme demo. They are not a statement of any real retailer's terms.

## [REF-01] Confirm a refund request
Ask for an order ID when a ticket is not linked to an order. Verify that the order belongs to the customer and review its status before discussing eligibility. Do not promise an amount or completion date that is not present in an approved payment record.

## [REF-02] Return must be reviewed before refund
The demo order workflow is placed, shipped, delivered, returned, refunded. Status can only advance one step at a time. A refund request for an order that is not marked returned requires staff to review and complete the applicable return steps first. Never skip a lifecycle state.

## [REF-03] Payment confirmation boundary
The demo API records order workflow status only. It does not initiate a payment, contact a bank, or verify a transfer. A status of refunded is not proof that money reached the customer. Staff must verify the payment processor or finance ledger before telling a customer a refund was issued.

## [REF-04] Customer response standard
Acknowledge the request, state only verified order facts, explain the next review step, and avoid unsupported promises. Include a relevant internal policy reference in agent drafts. Send the reply through an approved support channel; the demo app does not send messages.
