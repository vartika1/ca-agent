# Other sources — AY 2026-27

Computation in `scripts/heads.py::other_sources_income`. AIS is the primary
document — banks report interest and companies report dividends there.

## Intake mapping
`other_sources`: savings_interest, fd_interest, dividends, p2p_interest,
other_interest, family_pension, winnings.

## Rules the engine applies
- Savings/FD/bond interest, dividends, P2P: slab rate, both regimes.
- Family pension: deduction of 1/3rd capped Rs 15k (old) / Rs 25k (new) —
  automatic once `family_pension` is set. (Pension from own ex-employer is
  SALARY, not here.)
- Winnings (lottery, contests, online gaming 115BBJ): flat 30%, no basic
  exemption, no rebate — `winnings` field. TDS 194B/194BA sits in AIS; claim it.
- 80TTA (Rs 10k savings interest) / 80TTB (Rs 50k all interest, 60+) are
  granted automatically by the deduction engine from these facts — old regime
  only.

## Interview questions
1. Confirm AIS's interest lines bank-by-bank ("HDFC says Rs 42,318 — sound
   right?"). Interest the bank reported but the user forgot is the #1 notice
   trigger — this confirmation IS the point.
2. FDs that matured or auto-renewed? (Interest accrues yearly even if not
   credited to savings; AIS usually has it — if the user tracked receipt-basis
   historically, stay consistent and note it.)
3. Gifts above Rs 50k this year? From whom? (Relatives per the defined list +
   wedding gifts = exempt; others = fully taxable once total crosses Rs 50k —
   add to other_interest with a note, and record the giver relationship.)
4. Any lottery/game-show/online gaming wins? (Users hide these; the 30% TDS in
   AIS reveals them anyway — better declared.)

## Traps
- **Mailbox documents may belong to FAMILY, not the taxpayer (live-learned).**
  A bank/FD/deposit certificate arriving in the user's inbox — even addressed
  to their name — may be a joint account or one they merely MANAGE for a
  parent/spouse. NEVER fold a mailbox-found account into the return without
  confirming it is the taxpayer's own income. The authority for what IS the
  taxpayer's is **AIS (PAN-linked)**: income under the taxpayer's PAN appears
  in their AIS; a relative's account (different PAN) does not. So a
  suspiciously-low AIS interest figure is often correct — the larger deposits
  are a relative's, not hidden. Verify ownership before adding; respect the
  relative's privacy (don't open/parse their statement).
- FD interest accrues yearly (taxable even if not paid out); it is a known
  AIS-gap for cumulative deposits BELOW TDS thresholds — worth a bank
  interest-certificate check, but only for accounts confirmed as the
  taxpayer's own.
- 194R "benefits or perquisites" entries from crypto/fintech platforms
  (e.g. Bitcipher Labs = CoinSwitch) are usually small referral/reward values:
  count as misc other-sources income AND treat as platform-detection signal
  (ask for that platform's statement). A Rs 67 reward does NOT make the user
  a business filer.
- Dividend TDS (194) kicks in above Rs 5k per company — all in AIS; the
  reconciler will find unclaimed credits.
- Savings interest is taxable even under the new regime (80TTA is old-only) —
  users assume it's exempt; it isn't, only deducted.
- Interest on income-tax REFUND (s.244A) from last year is itself taxable this
  year — it's in AIS; include it in other_interest.
