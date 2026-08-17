#!/usr/bin/env python3
"""Deep pre-upload verification of the utility's SIGNED ITR JSON.

Why: the portal answers a malformed value with a generic "ITD-EXEC2003 …
technical error" and you lose a whole regenerate cycle finding it. The utility's
own Internal Validation does NOT catch these. This script hunts the exact
malformation classes that have caused real ITD-EXEC2003 failures.

  python3 scripts/verify_signed_json.py <signed_upload.json> [schema.json]

Exit code 0 = safe to upload; 1 = fix before uploading.
"""
import json, re, sys, unicodedata

ISO = re.compile(r'^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$')
DATEY = re.compile(r'date|dt$|dtls?date', re.I)
LOOKS_DATE = re.compile(r'^\s*\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}')

blockers, warns = [], []


def walk(node, path=''):
    if isinstance(node, dict):
        for k, v in node.items():
            walk(v, f'{path}/{k}')
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, f'{path}[{i}]')
    else:
        check(node, path)


def check(v, path):
    key = path.rsplit('/', 1)[-1].split('[')[0]
    if isinstance(v, str):
        # 1. trailing/leading whitespace or stray punctuation (the real killer)
        if v != v.strip():
            blockers.append(f'{path} = {v!r} — leading/trailing whitespace')
        if v.strip().endswith((',', ';', '.', '-', '/')) and not v.strip().endswith('...'):
            blockers.append(f'{path} = {v!r} — trailing punctuation inside string')
        # 2. dates must be ISO YYYY-MM-DD
        if DATEY.search(key) or LOOKS_DATE.match(v):
            if v.strip() and not ISO.match(v.strip()):
                blockers.append(f'{path} = {v!r} — date not ISO YYYY-MM-DD')
        # 3. empty strings where the utility should have omitted the key
        if v == '':
            warns.append(f'{path} — empty string (portal sometimes rejects)')
        # 4. non-ASCII / control characters
        if any(unicodedata.category(c)[0] == 'C' for c in v):
            blockers.append(f'{path} = {v!r} — contains control characters')
        if any(ord(c) > 127 for c in v):
            warns.append(f'{path} = {v!r} — non-ASCII character')
        # 5. a number hiding in a string
        if re.fullmatch(r'-?\d+', v) and key not in (
                'PAN', 'TAN', 'AadhaarCardNo', 'IFSCCode', 'BankAccountNo',
                'PinCode', 'MobileNo', 'IdentificationNo', 'PRANNum',
                'LoanAccNoOfBankOrInstnRefNo', 'AssesseeVerPAN', 'SWVersionNo'):
            warns.append(f'{path} = {v!r} — numeric value stored as string')
    elif isinstance(v, float):
        # rates may legitimately be fractional (e.g. 12.5% LTCG); AMOUNTS may not
        if v != int(v) and not re.search(r'percent|rate', key, re.I):
            blockers.append(f'{path} = {v} — fractional amount (ITR wants integers)')


def cross_foot(itr):
    """Independent arithmetic re-check of the headline figures."""
    ti = itr.get('PartB-TI', {})
    tti = itr.get('PartB_TTI', {})
    c = tti.get('ComputationOfTaxLiability', {})
    tp = tti.get('TaxPaid', {}).get('TaxesPaid', {})
    checks = []

    gti = ti.get('GrossTotalIncome')
    ded = ti.get('DeductionsUndSchVIADtl', {}).get('TotDeductUndSchVIA', 0)
    tot = ti.get('TotalIncome')
    if None not in (gti, tot):
        checks.append(('TotalIncome = GTI − Chapter VI-A', tot, gti - ded))

    agg = c.get('AggregateTaxInterestLiability')
    net = c.get('NetTaxLiability')
    intr = c.get('IntrstPay', {}).get('TotalIntrstPay', 0)
    if None not in (agg, net):
        checks.append(('Aggregate = NetTax + interest', agg, net + intr))

    paid = tp.get('TotalTaxesPaid')
    parts = sum(tp.get(k, 0) for k in
                ('AdvanceTax', 'TDS', 'TCS', 'SelfAssessmentTax'))
    if paid is not None:
        checks.append(('TotalTaxesPaid = sum of parts', paid, parts))

    bal = tti.get('TaxPaid', {}).get('BalTaxPayable')
    if None not in (agg, paid, bal):
        exact = max(0, agg - paid)
        # s.288B: tax payable is rounded to the nearest multiple of Rs 10
        rounded = int(round(exact / 10.0)) * 10
        checks.append(('BalTaxPayable = Aggregate − paid (s.288B rounded)',
                       bal, rounded if abs(bal - rounded) <= abs(bal - exact) else exact))

    sal = itr.get('ScheduleS', {})
    if sal:
        g = sal.get('TotalGrossSalary'); ex = sal.get('AllwncExtentExemptUs10', 0)
        net_s = sal.get('NetSalary'); d16 = sal.get('DeductionUS16', 0)
        inc = sal.get('TotIncUnderHeadSalaries')
        if None not in (g, net_s):
            checks.append(('NetSalary = gross − s.10 exempt', net_s, g - ex))
        if None not in (net_s, inc):
            checks.append(('Salary income = net − s.16', inc, net_s - d16))
        rows = sal.get('AllwncExemptUs10', {}).get('AllwncExemptUs10Dtls', [])
        if rows:
            checks.append(('s.10 exempt = sum of rows', ex,
                           sum(r.get('SalOthAmount', 0) for r in rows)))
    return checks


def main(fp, schema_fp=None):
    raw = open(fp, 'rb').read()
    print(f'\nDeep verification: {fp}\n' + '=' * 62)

    if raw[:1] == b'\xef':
        blockers.append('file starts with a UTF-8 BOM — strip it')
    try:
        doc = json.loads(raw)
    except Exception as e:
        print(f'FATAL: not valid JSON — {e}'); return 1

    itr = doc.get('ITR', {})
    form = next((f for f in ('ITR1', 'ITR2', 'ITR3', 'ITR4') if f in itr), None)
    if not form:
        print('FATAL: no ITR1..4 root'); return 1
    body = itr[form]

    walk(doc)

    dg = body.get('CreationInfo', {}).get('Digest')
    if not dg or dg in ('-', ''):
        blockers.append('CreationInfo.Digest missing — file is NOT utility-signed; '
                        'the portal will reject it. Re-download from the utility.')

    if schema_fp:
        try:
            from jsonschema import Draft4Validator
            errs = sorted(Draft4Validator(json.load(open(schema_fp)))
                          .iter_errors(doc), key=lambda e: str(e.path))
            for e in errs[:15]:
                blockers.append('schema: /' + '/'.join(str(x) for x in e.path)
                                + f' — {e.message[:110]}')
            if errs:
                blockers.append(f'schema: {len(errs)} total schema violations')
        except ImportError:
            warns.append('jsonschema not installed — schema check skipped')

    print('\nArithmetic cross-check (independent of the utility):')
    for label, got, exp in cross_foot(body):
        ok = (got == exp)
        print(f'  {"OK " if ok else "MISMATCH"}  {label}: {got:,} '
              + ('' if ok else f'(expected {exp:,})'))
        if not ok:
            blockers.append(f'arithmetic: {label} — {got} vs {exp}')

    print()
    if blockers:
        print(f'BLOCKING — fix before uploading ({len(blockers)}):')
        for b in blockers:
            print('   *', b)
    if warns:
        print(f'\nAdvisory ({len(warns)}):')
        for w in warns[:12]:
            print('   -', w)
    if not blockers:
        print('SAFE TO UPLOAD — no ITD-EXEC2003-class defects found.')
    return 1 if blockers else 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
