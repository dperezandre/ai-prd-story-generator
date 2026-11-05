# Customer referral program

## Problem

Acquiring customers through paid channels is getting more expensive, while satisfied customers have no easy way to recommend the store. Marketing cannot measure word of mouth today, so it is neither encouraged nor funded.

## As-is

- Customers cannot invite friends or earn rewards for new customers.
- Acquisition relies on paid channels only.

## To-be

- Each customer has a unique referral link.
- A friend arriving through the link sees the discount before checkout.
- The referrer is credited after the friend's first completed order.

## Personas

- Returning customer: wants to recommend the store and be rewarded without asking support
- Referred friend: wants to know the offer is real before creating an account
- Program owner (marketing): wants to grow acquisition and control the cost of rewards

## Goals

- Increase the share of new customers acquired through recommendations
- Reward both the referrer and the friend in a way that is simple to understand
- Keep the cost of the program predictable and resistant to abuse

## Success metrics

- Share of new customers acquired through referral: increase (baseline not provided)
- Referral conversion rate (invited friends who place a first order): increase (baseline not provided)
- Reward cost per referred customer: stay below the paid-channel acquisition cost

## Systems and modules

- Web store - Checkout
- Customer account - Referral area

## In scope

- Unique referral link per customer
- Discount for the friend and credit for the referrer after the friend's first order
- Referrer view of invitation status
- Basic abuse prevention

## Out of scope

- Referral through social media APIs or contact import
- Multi-level or tiered rewards

## Requirements

- The system must give every customer a unique referral link
- The system must show the friend's discount before checkout when they arrive through a referral link
- The system must credit the referrer after the friend's first order is completed
- The system must let the referrer see the status of each invitation
- The system must block self-referral and repeated rewards for the same friend

## Business rules

- RN01: A referral link belongs to exactly one customer.
- RN02: The referrer is credited only after the friend's first order is completed.
- RN03: A customer cannot refer themselves, and a friend can trigger only one reward.

## Expected returns

- Experience: share of new customers acquired through referral
- Financial: acquisition cost per customer (baseline not provided)

## Risks

- Reward abuse by fake accounts - mitigation: reward only after a completed, paid first order
- Discount cost exceeds the budget - mitigation: cap total rewards per customer per month

## Assumptions

- Assumption: the reward is a store credit, not cash; the idea does not say which
- Assumption: customers already have accounts and can sign in

## Open questions

- What are the reward amounts and who funds them?
- What is today's acquisition cost per customer, to set the break-even point?

## User stories

### S1 — Copy my referral link

As a returning customer, I want to copy my referral link from my account page in one step so that I can share it without asking support

Share and track · Must · 3 pts

**Acceptance criteria**

```gherkin
Scenario: Referral link is copied for sharing
  Given a returning customer is signed in
  When the customer chooses to copy their referral link
  Then the link is available to paste
  And the link identifies the customer as the referrer

Scenario: Each customer has a different link
  Given two returning customers are signed in
  When each opens their referral link
  Then the two links are different
```

### S2 — Receive credit for a friend's first order

As a returning customer, I want to receive store credit when my friend completes a first order so that I am rewarded for recommending the store

Share and track · Must · 5 pts

**Acceptance criteria**

```gherkin
Scenario: Referrer is credited after the first paid order
  Given a friend arrived through a customer's referral link
  And the friend placed and paid a first order
  When the order is marked as completed
  Then the referrer receives the referral credit
  And the referrer is notified of the credit

Scenario: Credit is not given for an unpaid order
  Given a friend arrived through a referral link
  And the friend's order payment failed
  When the order is cancelled
  Then the referrer receives no credit

Scenario: Credit is given only once per friend
  Given a referrer was already credited for a friend
  When the friend completes a second order
  Then the referrer receives no additional credit
```

### S3 — See the friend discount from the referral link

As a referred friend, I want to see my discount when I arrive through a referral link and again at checkout so that I know the offer is real before I buy

Referred friend experience · Must · 3 pts

**Acceptance criteria**

```gherkin
Scenario: Discount is shown on arrival
  Given a visitor opens a valid referral link
  When the store page loads
  Then the visitor sees the friend discount offer
  And the visitor sees who invited them

Scenario: Discount is applied at checkout
  Given a visitor arrived through a valid referral link and added items to the cart
  When the visitor reaches checkout
  Then the discount appears as a line in the order summary

Scenario: Invalid link shows no discount
  Given a visitor opens a referral link that does not exist
  When the store page loads
  Then no discount is shown
  And the visitor can still browse and buy at regular prices
```

### S4 — Check the status of my invitations

As a returning customer, I want to see whether each invited friend has registered or ordered so that I know when to expect my credit

Referred friend experience · Should · 5 pts

**Acceptance criteria**

```gherkin
Scenario: Referrer sees each stage
  Given a customer has invited three friends, one registered and one ordered
  When the customer opens the referral page
  Then the customer sees counts for invited, registered and ordered

Scenario: Empty state explains how to start
  Given a customer has not shared the link yet
  When the customer opens the referral page
  Then the customer sees how the program works and the link to copy
```

### S5 — Block self-referral

As a program owner, I want the system to refuse rewards when the referrer and the friend are the same person so that reward cost is not wasted on fake referrals

Program integrity · Should · 5 pts

**Acceptance criteria**

```gherkin
Scenario: Same customer cannot reward themselves
  Given a customer opens their own referral link in a new account with the same payment method
  When the new account completes a first order
  Then no discount is given to the new account
  And no credit is given to the referrer

Scenario: Legitimate referral is unaffected
  Given a friend with a different account and payment method arrives through a referral link
  When the friend completes a first order
  Then both the discount and the credit are granted
```
