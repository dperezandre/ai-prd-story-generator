# Abandoned cart recovery

## Problem

Many shoppers add items to the cart and leave without paying. The store has no follow-up, so interested customers are lost, and any follow-up that is too aggressive risks annoying them and breaching consent rules.

## Personas

- Hesitant shopper: left items in the cart and may return if reminded at the right moment
- E-commerce manager: wants to recover revenue without damaging the brand

## Goals

- Recover a measurable share of abandoned carts
- Keep reminders relevant, limited in number and easy to opt out of

## Success metrics

- Recovered cart rate (abandoned carts that end in a paid order): increase (baseline not provided)
- Unsubscribe rate from reminder emails: stay low (threshold not provided)

## In scope

- Reminder email after a cart is abandoned
- One follow-up reminder
- Link that restores the cart
- Unsubscribe and stop-on-purchase rules

## Out of scope

- SMS or push reminders
- Personalized discount offers

## Requirements

- The system must send a reminder email to a signed-in shopper who abandoned a cart
- The system must send at most one follow-up reminder
- The system must restore the cart contents when the shopper follows the email link
- The system must stop reminders once the shopper completes a purchase
- The system must honour an unsubscribe request in every reminder

## Risks

- Privacy and consent rules for marketing email - mitigation: send only to shoppers who accepted communications, with one-click unsubscribe
- Items out of stock when the shopper returns - mitigation: tell the shopper which items are no longer available

## Assumptions

- Assumption: a cart counts as abandoned after 1 hour without checkout; the idea does not define it
- Assumption: only signed-in shoppers can be reached, because the store has their email

## Open questions

- What is the right waiting time before the first reminder?
- Which consent record does the store keep for marketing email?

## User stories

### S1 — Send a reminder after cart abandonment

As a hesitant shopper, I want to receive one email reminding me of the items I left in my cart so that I can finish the purchase without searching again

Reminder emails · Must · 5 pts

**Acceptance criteria**

```gherkin
Scenario: Reminder is sent after the waiting time
  Given a signed-in shopper who accepted emails left items in the cart
  When one hour passes without checkout
  Then the shopper receives a reminder listing the items left in the cart

Scenario: No reminder without consent
  Given a signed-in shopper who did not accept marketing emails left items in the cart
  When one hour passes without checkout
  Then no reminder is sent
```

### S2 — Send one follow-up after 24 hours

As a e-commerce manager, I want a single follow-up reminder 24 hours after the first one when the cart is still open so that more shoppers come back without being over-contacted

Reminder emails · Should · 3 pts

**Acceptance criteria**

```gherkin
Scenario: Follow-up is sent once
  Given a shopper received a first reminder and did not buy
  When 24 hours pass
  Then the shopper receives one follow-up reminder

Scenario: No third reminder
  Given a shopper received a reminder and a follow-up and did not buy
  When more time passes
  Then no further reminder is sent
```

### S3 — Restore my cart from the email link

As a hesitant shopper, I want to return to a cart with my items already in it when I follow the email link so that I can go straight to checkout

Reminder emails · Must · 5 pts

**Acceptance criteria**

```gherkin
Scenario: Cart is restored
  Given a shopper received a reminder for a cart with two items
  When the shopper follows the link
  Then the cart shows the same two items
  And the shopper can proceed to checkout

Scenario: Unavailable items are explained
  Given one of the two items is now out of stock
  When the shopper follows the link
  Then the cart contains the available item
  And the shopper is told which item is no longer available
```

### S4 — Unsubscribe from reminders

As a hesitant shopper, I want to stop receiving cart reminders with one click from any reminder so that my choice is respected immediately

Customer control · Must · 2 pts

**Acceptance criteria**

```gherkin
Scenario: Unsubscribe takes effect immediately
  Given a shopper received a reminder
  When the shopper uses the unsubscribe link
  Then the shopper is confirmed as unsubscribed
  And no further cart reminders are sent

Scenario: Pending follow-up is cancelled
  Given a shopper received a first reminder and has a follow-up scheduled
  When the shopper unsubscribes
  Then the scheduled follow-up is not sent
```

### S5 — Stop reminders after purchase

As a hesitant shopper, I want reminders to stop as soon as I complete my order so that I am not nagged about something I already bought

Customer control · Should · 3 pts

**Acceptance criteria**

```gherkin
Scenario: Reminder stops after purchase
  Given a shopper received a first reminder
  When the shopper completes the order before the follow-up
  Then the follow-up is not sent

Scenario: Partial purchase keeps the rest
  Given a shopper left three items and buys one of them
  When the follow-up time arrives
  Then the follow-up lists only the two remaining items
```
