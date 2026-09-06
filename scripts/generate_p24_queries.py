# scripts/generate_p24_queries.py
"""
Generates the Phase 2.4 evaluation dataset (p24_queries_v1.jsonl).
150 structured layman legal queries across 16 domains, procedure, central/state jurisdictions, and difficulty tiers.
"""

import json
from pathlib import Path

out_dir = Path("d:/Abishek/eval/queries")
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / "p24_queries_v1.jsonl"

DOMAINS = [
    "Consumer Protection", "Employment & Labour", "Workplace Rights",
    "Contracts & Agreements", "Property Law", "Family Law", "Criminal Law",
    "Motor Vehicles / Traffic", "Cyber Law / Digital Law", "Banking & Finance",
    "Taxation", "Company / Corporate Law", "Business & Entrepreneurship",
    "Intellectual Property", "Environmental Law", "Constitutional Rights"
]

queries = []

# Helper builder
def add_q(qid, text, domain, proc=False, jur="central_only", qtype="easy", sec_tags=None, diff=None, paraphrase=None):
    queries.append({
        "query_id": qid,
        "query_text": text,
        "domain": domain,
        "procedure_related": proc,
        "jurisdiction_expectation": jur,
        "query_type": qtype,
        "secondary_tags": sec_tags or [],
        "difficulty_category": diff,
        "precise_paraphrase": paraphrase
    })

# 1. Consumer Protection (10 queries)
add_q("p24-consumer-001", "Can I return a defective electronic product bought online if seller refuses replacement?", "Consumer Protection", False, "central_only", "easy")
add_q("p24-consumer-002", "How do I file a consumer complaint against a builder for delay in flat possession?", "Consumer Protection", True, "central_only", "easy", ["procedure"])
add_q("p24-consumer-003", "What is the fee and process to file a case in District Consumer Commission?", "Consumer Protection", True, "central_only", "easy", ["procedure"])
add_q("p24-consumer-004", "Is an e-commerce platform liable for fake products sold by third-party sellers?", "Consumer Protection", False, "central_only", "moderately_ambiguous")
add_q("p24-consumer-005", "Can a hospital be sued for medical negligence under Consumer Protection Act?", "Consumer Protection", False, "central_only", "judgment_focused")
add_q("p24-consumer-006", "What is the penalty for misleading advertisements under CPA 2019?", "Consumer Protection", False, "central_only", "legislation_focused")
add_q("p24-consumer-007", "Airline lost my baggage on domestic flight, can I claim compensation in consumer court?", "Consumer Protection", False, "central_only", "moderately_ambiguous")
add_q("p24-consumer-008", "My gym refused refund after closing down within one month. What legal options do I have?", "Consumer Protection", False, "central_only", "easy")
add_q("p24-consumer-009", "Is misleading insurance policy selling covered under unfair trade practices?", "Consumer Protection", False, "central_only", "mixed_legislation_judgment")
add_q("p24-consumer-010", "What are the rules for dark patterns in online shopping under Consumer Protection guidelines?", "Consumer Protection", False, "central_only", "legislation_focused")

# 2. Employment & Labour (10 queries)
add_q("p24-employment-001", "What is the legal notice period required if not specified in job offer letter?", "Employment & Labour", False, "jurisdiction_ambiguous", "easy")
add_q("p24-employment-002", "Can an employer hold my original educational certificates legally?", "Employment & Labour", False, "central_only", "easy")
add_q("p24-employment-003", "What are shop closing hours and overtime payment rules for private IT office in Bangalore?", "Employment & Labour", False, "state_specific: Karnataka", "jurisdiction_sensitive")
add_q("p24-employment-004", "Am I eligible for gratuity if I resign after completing 4 years and 7 months?", "Employment & Labour", False, "central_only", "legislation_focused")
add_q("p24-employment-005", "Is non-compete clause enforceable in India after employee resigns?", "Employment & Labour", False, "central_only", "judgment_focused")
add_q("p24-employment-006", "My employer is not depositing PF contribution despite deducting from salary.", "Employment & Labour", True, "central_only", "easy")
add_q("p24-employment-007", "Can a factory worker be terminated without notice or domestic inquiry?", "Employment & Labour", False, "central_only", "mixed_legislation_judgment")
add_q("p24-employment-008", "What are worker safety standards under Factories Act for hazardous chemical handling?", "Employment & Labour", False, "central_only", "legislation_focused")
add_q("p24-employment-009", "Company terminated me while I was on approved medical leave.", "Employment & Labour", False, "central_only", "moderately_ambiguous")
add_q("p24-employment-010", "What is the maximum probation period permissible under labour laws?", "Employment & Labour", False, "jurisdiction_ambiguous", "easy")

# 3. Workplace Rights (9 queries)
add_q("p24-workplace-001", "What are the mandatory requirements for Internal Complaints Committee under POSH Act?", "Workplace Rights", False, "central_only", "legislation_focused")
add_q("p24-workplace-002", "How many weeks of paid maternity leave am I entitled to for first child?", "Workplace Rights", False, "central_only", "easy")
add_q("p24-workplace-003", "Can an employer terminate a female employee while she is on maternity leave?", "Workplace Rights", False, "central_only", "easy")
add_q("p24-workplace-004", "What is the legal procedure to lodge workplace sexual harassment complaint?", "Workplace Rights", True, "central_only", "easy", ["procedure"])
add_q("p24-workplace-005", "Are contract employees entitled to maternity benefits under Maternity Benefit Act?", "Workplace Rights", False, "central_only", "judgment_focused")
add_q("p24-workplace-006", "Is equal pay for equal work a legally enforceable right in private sector?", "Workplace Rights", False, "central_only", "mixed_legislation_judgment")
add_q("p24-workplace-007", "What are crèche facility requirements for workplace with over 50 employees?", "Workplace Rights", False, "central_only", "legislation_focused")
add_q("p24-workplace-008", "Boss demands working 14 hours daily without overtime pay.", "Workplace Rights", False, "jurisdiction_ambiguous", "moderately_ambiguous")
add_q("p24-workplace-009", "Is night shift work allowed for female employees in Maharashtra factories?", "Workplace Rights", False, "state_specific: Maharashtra", "jurisdiction_sensitive")

# 4. Contracts & Agreements (10 queries)
add_q("p24-contracts-001", "Is an un-stamped agreement on simple white paper legally valid in court?", "Contracts & Agreements", False, "jurisdiction_ambiguous", "easy")
add_q("p24-contracts-002", "What makes a contract void due to coercion or undue influence under Contract Act?", "Contracts & Agreements", False, "central_only", "legislation_focused")
add_q("p24-contracts-003", "Is an oral agreement legally binding for sale of movable goods?", "Contracts & Agreements", False, "central_only", "easy")
add_q("p24-contracts-004", "Can a minor enter into a legally enforceable business agreement?", "Contracts & Agreements", False, "central_only", "easy")
add_q("p24-contracts-005", "What is liquidated damages vs penalty clause under Indian Contract Act Section 74?", "Contracts & Agreements", False, "central_only", "judgment_focused")
add_q("p24-contracts-006", "Does email exchange constitute a valid written contract in India?", "Contracts & Agreements", False, "central_only", "mixed_legislation_judgment")
add_q("p24-contracts-007", "What happens if a contract becomes impossible to perform due to lockdown or force majeure?", "Contracts & Agreements", False, "central_only", "judgment_focused")
add_q("p24-contracts-008", "Can security deposit be forfeited without showing actual loss in commercial lease?", "Contracts & Agreements", False, "central_only", "judgment_focused")
add_q("p24-contracts-009", "Is an online click-wrap agreement legally enforceable?", "Contracts & Agreements", False, "central_only", "moderately_ambiguous")
add_q("p24-contracts-010", "What is the limitation period to file suit for breach of contract?", "Contracts & Agreements", True, "central_only", "legislation_focused", ["procedure"])

# 5. Property Law (10 queries)
add_q("p24-property-001", "What is the mandatory registration rule for tenant lease agreements exceeding 11 months?", "Property Law", False, "central_only", "easy")
add_q("p24-property-002", "Can ancestral property be sold by father without consent of daughters?", "Property Law", False, "central_only", "judgment_focused")
add_q("p24-property-003", "What is eviction procedure for residential tenant under Maharashtra Rent Control Act?", "Property Law", True, "state_specific: Maharashtra", "jurisdiction_sensitive", ["procedure"])
add_q("p24-property-004", "Does an un-registered sale deed transfer legal ownership of immovable land?", "Property Law", False, "central_only", "legislation_focused")
add_q("p24-property-005", "What are the equal coparcenary rights of daughters in Hindu Undivided Family property?", "Property Law", False, "central_only", "mixed_legislation_judgment")
add_q("p24-property-006", "How to challenge illegal encroachment on private land by neighbor?", "Property Law", True, "central_only", "easy", ["procedure"])
add_q("p24-property-007", "What is gift deed stamp duty requirement for transfer of house to legal heir in Delhi?", "Property Law", False, "state_specific: Delhi", "jurisdiction_sensitive")
add_q("p24-property-008", "Can a landlord disconnect electricity or water supply to force tenant eviction?", "Property Law", False, "jurisdiction_ambiguous", "easy")
add_q("p24-property-009", "What is adverse possession period to claim ownership of land?", "Property Law", False, "central_only", "judgment_focused")
add_q("p24-property-010", "Is RERA registration mandatory for real estate project under 500 square meters?", "Property Law", False, "central_only", "legislation_focused")

# 6. Family Law (10 queries)
add_q("p24-family-001", "What are grounds for mutual consent divorce under Hindu Marriage Act Section 13B?", "Family Law", False, "central_only", "easy")
add_q("p24-family-002", "What is minimum mandatory cooling-off period for mutual consent divorce?", "Family Law", False, "central_only", "judgment_focused")
add_q("p24-family-003", "Can a wife claim interim maintenance under Section 125 CrPC if she is working?", "Family Law", False, "central_only", "judgment_focused")
add_q("p24-family-004", "What are child custody factors considered by court for minor under 5 years?", "Family Law", False, "central_only", "judgment_focused")
add_q("p24-family-005", "Can Hindu father disinherit married daughter from self-acquired property by Will?", "Family Law", False, "central_only", "easy")
add_q("p24-family-006", "What is procedure to register inter-faith marriage under Special Marriage Act?", "Family Law", True, "central_only", "legislation_focused", ["procedure"])
add_q("p24-family-007", "Can a husband claim maintenance from wife under Hindu Marriage Act Section 24?", "Family Law", False, "central_only", "legislation_focused")
add_q("p24-family-008", "What is legal status and property rights of child born from live-in relationship?", "Family Law", False, "central_only", "judgment_focused")
add_q("p24-family-009", "What constitutes cruelty as a ground for contested divorce under Hindu law?", "Family Law", False, "central_only", "mixed_legislation_judgment")
add_q("p24-family-010", "Is registration of marriage mandatory across all states in India?", "Family Law", False, "jurisdiction_ambiguous", "jurisdiction_sensitive")

# 7. Criminal Law (10 queries)
add_q("p24-criminal-001", "What is difference between bailable offence and non-bailable offence under Code of Criminal Procedure?", "Criminal Law", False, "central_only", "easy")
add_q("p24-criminal-002", "What are legal rights of an arrested person under Article 22 and Section 50 CrPC?", "Criminal Law", True, "central_only", "easy", ["procedure"])
add_q("p24-criminal-003", "Can police refuse to register FIR for cognizable offence?", "Criminal Law", True, "central_only", "judgment_focused", ["procedure"])
add_q("p24-criminal-004", "What is procedure to apply for anticipatory bail under Section 438 CrPC?", "Criminal Law", True, "central_only", "legislation_focused", ["procedure"])
add_q("p24-criminal-005", "What constitutes offence of criminal breach of trust under IPC Section 405?", "Criminal Law", False, "central_only", "legislation_focused")
add_q("p24-criminal-006", "What is statutory bail period if police fail to file chargesheet within 60 or 90 days?", "Criminal Law", False, "central_only", "mixed_legislation_judgment")
add_q("p24-criminal-007", "Can private individual lodge zero FIR at any police station regardless of jurisdiction?", "Criminal Law", True, "central_only", "judgment_focused", ["procedure"])
add_q("p24-criminal-008", "What are penalties for filing false criminal case or perjury under IPC Section 191?", "Criminal Law", False, "central_only", "legislation_focused")
add_q("p24-criminal-009", "Is domestic violence complaint under DV Act civil or criminal proceeding?", "Criminal Law", False, "central_only", "mixed_legislation_judgment")
add_q("p24-criminal-010", "What is legal remedy if police assault or torture suspect in police custody?", "Criminal Law", True, "central_only", "judgment_focused", ["procedure"])

# 8. Motor Vehicles / Traffic (9 queries)
add_q("p24-traffic-001", "What is mandatory insurance requirement for commercial heavy vehicles under Motor Vehicles Act?", "Motor Vehicles / Traffic", False, "central_only", "easy")
add_q("p24-traffic-002", "What is legal procedure to claim compensation from MACT for road accident death?", "Motor Vehicles / Traffic", True, "central_only", "legislation_focused", ["procedure"])
add_q("p24-traffic-003", "Can traffic police seize vehicle or driving license for non-payment of e-challan?", "Motor Vehicles / Traffic", False, "jurisdiction_ambiguous", "jurisdiction_sensitive")
add_q("p24-traffic-004", "What is penalty for drink and drive under MV Act Section 185?", "Motor Vehicles / Traffic", False, "central_only", "easy")
add_q("p24-traffic-005", "Is helmet mandatory for pillion rider across all states in India?", "Motor Vehicles / Traffic", False, "jurisdiction_ambiguous", "jurisdiction_sensitive")
add_q("p24-traffic-006", "What is liability of vehicle owner if vehicle driven by minor causes fatal accident?", "Motor Vehicles / Traffic", False, "central_only", "legislation_focused")
add_q("p24-traffic-007", "What protection does Good Samaritan policy provide to bystanders helping accident victims?", "Motor Vehicles / Traffic", False, "central_only", "judgment_focused")
add_q("p24-traffic-008", "Can insurance company deny third party claim if driver had expired license?", "Motor Vehicles / Traffic", False, "central_only", "judgment_focused")
add_q("p24-traffic-009", "What is legal limit of blood alcohol concentration while driving in India?", "Motor Vehicles / Traffic", False, "central_only", "easy")

# 9. Cyber Law / Digital Law (10 queries)
add_q("p24-cyber-001", "What is penalty for identity theft and impersonation online under IT Act Section 66C?", "Cyber Law / Digital Law", False, "central_only", "easy")
add_q("p24-cyber-002", "How to report online financial fraud or UPI cyber scam to Cyber Crime portal?", "Cyber Law / Digital Law", True, "central_only", "easy", ["procedure"])
add_q("p24-cyber-003", "Is publishing private photographs without consent punishable under IT Act Section 66E?", "Cyber Law / Digital Law", False, "central_only", "legislation_focused")
add_q("p24-cyber-004", "What are data protection principles and consent requirements under DPDP Act 2023?", "Cyber Law / Digital Law", False, "central_only", "legislation_focused")
add_q("p24-cyber-005", "Are social media intermediaries legally required to remove un-lawful content within 36 hours?", "Cyber Law / Digital Law", False, "central_only", "legislation_focused")
add_q("p24-cyber-006", "What is legal admissibility requirement for electronic records and emails under Section 65B Evidence Act?", "Cyber Law / Digital Law", False, "central_only", "judgment_focused")
add_q("p24-cyber-007", "Can a bank be held liable if money stolen via SIM swap fraud without customer OTP sharing?", "Cyber Law / Digital Law", False, "central_only", "judgment_focused")
add_q("p24-cyber-008", "What is punishment for cyber stalking and harassment under IPC Section 354D?", "Cyber Law / Digital Law", False, "central_only", "easy")
add_q("p24-cyber-009", "Is hacking into private computer system bailable or non-bailable under IT Act?", "Cyber Law / Digital Law", False, "central_only", "legislation_focused")
add_q("p24-cyber-010", "What are rules regarding mandatory 24-hour reporting of cyber security incidents to CERT-In?", "Cyber Law / Digital Law", False, "central_only", "legislation_focused")

# 10. Banking & Finance (10 queries)
add_q("p24-banking-001", "What is legal remedy for cheque bounce under Negotiable Instruments Act Section 138?", "Banking & Finance", True, "central_only", "easy", ["procedure"])
add_q("p24-banking-002", "What is mandatory demand notice timeline before filing Section 138 NI Act case?", "Banking & Finance", True, "central_only", "legislation_focused", ["procedure"])
add_q("p24-banking-003", "Can loan recovery agents threaten or visit borrower home after 7 PM legally?", "Banking & Finance", False, "central_only", "judgment_focused")
add_q("p24-banking-004", "What is Ombudsman complaint procedure for unauthorized credit card charges?", "Banking & Finance", True, "central_only", "easy", ["procedure"])
add_q("p24-banking-005", "Can bank freeze entire savings account for minor loan EMI default?", "Banking & Finance", False, "central_only", "judgment_focused")
add_q("p24-banking-006", "What is SARFAESI Act notice period given by bank before taking symbolic possession of mortgaged property?", "Banking & Finance", False, "central_only", "legislation_focused")
add_q("p24-banking-007", "Is guarantor equally liable as primary borrower for repaying bank loan?", "Banking & Finance", False, "central_only", "judgment_focused")
add_q("p24-banking-008", "What is RBI customer protection limit for zero liability in unauthorized electronic transaction?", "Banking & Finance", False, "central_only", "legislation_focused")
add_q("p24-banking-009", "Can bank deduct money from fixed deposit without borrower consent under banker right of lien?", "Banking & Finance", False, "central_only", "judgment_focused")
add_q("p24-banking-010", "What is procedure to approach Debt Recovery Tribunal for home loan auction challenge?", "Banking & Finance", True, "central_only", "legislation_focused", ["procedure"])

# 11. Taxation (9 queries)
add_q("p24-taxation-001", "What is penalty for non-filing of Income Tax Return before due date under Section 234F?", "Taxation", False, "central_only", "easy")
add_q("p24-taxation-002", "Can income tax officer issue reassessment notice after 3 years under Section 148?", "Taxation", False, "central_only", "legislation_focused")
add_q("p24-taxation-003", "What is GST registration threshold limit for goods supplier in special category states?", "Taxation", False, "jurisdiction_ambiguous", "jurisdiction_sensitive")
add_q("p24-taxation-004", "Is gift received from relative taxable under Income Tax Act Section 56(2)?", "Taxation", False, "central_only", "easy")
add_q("p24-taxation-005", "What is penalty for fake GST input tax credit claim under CGST Act?", "Taxation", False, "central_only", "legislation_focused")
add_q("p24-taxation-006", "How to file appeal before Income Tax Appellate Tribunal against CIT Assessment Order?", "Taxation", True, "central_only", "easy", ["procedure"])
add_q("p24-taxation-007", "Is agriculture income completely tax free or considered for slab rate determination?", "Taxation", False, "central_only", "mixed_legislation_judgment")
add_q("p24-taxation-008", "What is TDS deduction requirement when purchasing property worth over 50 Lakhs?", "Taxation", False, "central_only", "easy")
add_q("p24-taxation-009", "Can GST department arrest taxpayer without issuing show cause notice?", "Taxation", False, "central_only", "judgment_focused")

# 12. Company / Corporate Law (9 queries)
add_q("p24-company-001", "What is minimum board meetings count required per calendar year under Companies Act 2013?", "Company / Corporate Law", False, "central_only", "easy")
add_q("p24-company-002", "What is procedure for voluntary strike off of private limited company under Section 248?", "Company / Corporate Law", True, "central_only", "legislation_focused", ["procedure"])
add_q("p24-company-003", "What are personal civil liabilities of director for company fraud under Section 447?", "Company / Corporate Law", False, "central_only", "legislation_focused")
add_q("p24-company-004", "What is threshold requirement for shareholders to file operation and mismanagement petition under Section 241?", "Company / Corporate Law", False, "central_only", "mixed_legislation_judgment")
add_q("p24-company-005", "Is One Person Company required to hold Annual General Meeting?", "Company / Corporate Law", False, "central_only", "easy")
add_q("p24-company-006", "What is CSR spend mandate percentage for companies with net profit over 5 crore?", "Company / Corporate Law", False, "central_only", "easy")
add_q("p24-company-007", "Can a disqualified director be re-appointed during 5-year disqualification period?", "Company / Corporate Law", False, "central_only", "judgment_focused")
add_q("p24-company-008", "What is procedure for NCLT approval of scheme of merger or amalgamation?", "Company / Corporate Law", True, "central_only", "legislation_focused", ["procedure"])
add_q("p24-company-009", "What constitutes related party transaction requiring audit committee approval?", "Company / Corporate Law", False, "central_only", "legislation_focused")

# 13. Business & Entrepreneurship (9 queries)
add_q("p24-biz-001", "What is MSME delayed payment interest rate rule under MSMED Act Section 16?", "Business & Entrepreneurship", False, "central_only", "easy")
add_q("p24-biz-002", "How to file complaint before Samadhaan portal for unpaid MSME supplier invoices?", "Business & Entrepreneurship", True, "central_only", "easy", ["procedure"])
add_q("p24-biz-003", "Is FSSAI food license mandatory for home baker selling online?", "Business & Entrepreneurship", False, "central_only", "easy")
add_q("p24-biz-004", "What is liability difference between Partnership firm and Limited Liability Partnership?", "Business & Entrepreneurship", False, "central_only", "easy")
add_q("p24-biz-005", "Can trade license be revoked by Municipal Corporation without opportunity of hearing?", "Business & Entrepreneurship", False, "state_specific: Karnataka", "jurisdiction_sensitive")
add_q("p24-biz-006", "What are tax holiday benefits under Startup India scheme Section 80-IAC?", "Business & Entrepreneurship", False, "central_only", "legislation_focused")
add_q("p24-biz-007", "Is shop and establishment registration required for remote work software consultancy?", "Business & Entrepreneurship", False, "jurisdiction_ambiguous", "jurisdiction_sensitive")
add_q("p24-biz-008", "What happens if partnership firm is unregistered when filing civil breach suit?", "Business & Entrepreneurship", False, "central_only", "legislation_focused")
add_q("p24-biz-009", "Can a co-founder be removed without board resolution in private company?", "Business & Entrepreneurship", False, "central_only", "moderately_ambiguous")

# 14. Intellectual Property (9 queries)
add_q("p24-ip-001", "What is validity period of registered trademark in India before renewal is needed?", "Intellectual Property", False, "central_only", "easy")
add_q("p24-ip-002", "What constitutes copyright infringement of software code under Copyright Act Section 51?", "Intellectual Property", False, "central_only", "mixed_legislation_judgment")
add_q("p24-ip-003", "Can business brand name be registered if identical phonetically to registered trademark?", "Intellectual Property", False, "central_only", "judgment_focused")
add_q("p24-ip-004", "What is fair use exception for educational usage under Copyright Act Section 52?", "Intellectual Property", False, "central_only", "judgment_focused")
add_q("p24-ip-005", "What is term of patent protection in India from filing date?", "Intellectual Property", False, "central_only", "easy")
add_q("p24-ip-006", "How to file opposition against published trademark application within 4 months?", "Intellectual Property", True, "central_only", "easy", ["procedure"])
add_q("p24-ip-007", "Can recipe or cooking method be patented under Indian Patent Act?", "Intellectual Property", False, "central_only", "legislation_focused")
add_q("p24-ip-008", "What is Anton Piller order granted by court in IP passing off suit?", "Intellectual Property", True, "central_only", "judgment_focused", ["procedure"])
add_q("p24-ip-009", "Is unregistered trademark entitled to passing off protection in court?", "Intellectual Property", False, "central_only", "judgment_focused")

# 15. Environmental Law (8 queries)
add_q("p24-env-001", "What is environmental clearance requirement under EIA Notification 2006 for construction projects?", "Environmental Law", False, "central_only", "legislation_focused")
add_q("p24-env-002", "How to lodge complaint before National Green Tribunal for river pollution?", "Environmental Law", True, "central_only", "easy", ["procedure"])
add_q("p24-env-003", "What is penalty for operating industrial factory without Consent to Operate from State Pollution Control Board?", "Environmental Law", False, "jurisdiction_ambiguous", "jurisdiction_sensitive")
add_q("p24-env-004", "What is polluter pays principle laid down by Supreme Court in environmental cases?", "Environmental Law", False, "central_only", "judgment_focused")
add_q("p24-env-005", "Are plastics under 120 microns completely banned under Plastic Waste Management Rules?", "Environmental Law", False, "central_only", "legislation_focused")
add_q("p24-env-006", "Can residential housing society be fined for failing to install rainwater harvesting system in Bangalore?", "Environmental Law", False, "state_specific: Karnataka", "jurisdiction_sensitive")
add_q("p24-env-007", "What is legal noise limit in residential zone during night hours under Noise Pollution Rules?", "Environmental Law", False, "central_only", "easy")
add_q("p24-env-008", "Is hazardous waste dumping punishable with imprisonment under Environment Protection Act?", "Environmental Law", False, "central_only", "legislation_focused")

# 16. Constitutional Rights (9 queries)
add_q("p24-const-001", "What is difference between Habeas Corpus and Mandamus writ under Article 226?", "Constitutional Rights", True, "central_only", "easy", ["procedure"])
add_q("p24-const-002", "Is Right to Privacy a fundamental right under Article 21 following Puttaswamy judgment?", "Constitutional Rights", False, "central_only", "judgment_focused")
add_q("p24-const-003", "Can fundamental rights be suspended during National Emergency under Article 359?", "Constitutional Rights", False, "central_only", "legislation_focused")
add_q("p24-const-004", "What is reasonable restriction on freedom of speech under Article 19(2)?", "Constitutional Rights", False, "central_only", "mixed_legislation_judgment")
add_q("p24-const-005", "Can a private citizen file Public Interest Litigation directly in Supreme Court under Article 32?", "Constitutional Rights", True, "central_only", "easy", ["procedure"])
add_q("p24-const-006", "What is legal procedure to seek legal aid under Legal Services Authorities Act?", "Constitutional Rights", True, "central_only", "easy", ["procedure"])
add_q("p24-const-007", "Is reservation ceiling limit of 50% binding unless constitutional amendment provides otherwise?", "Constitutional Rights", False, "central_only", "judgment_focused")
add_q("p24-const-008", "What constitutes basic structure of Constitution that cannot be amended?", "Constitutional Rights", False, "central_only", "judgment_focused")
add_q("p24-const-009", "Is right to free primary education up to age 14 a fundamental right under Article 21A?", "Constitutional Rights", False, "central_only", "easy")

# 17. Special / Difficult / Edge Cases (9 queries)
add_q("p24-diff-001", "my boss didn't pay my last salary and threatened to block my PF", "Employment & Labour", False, "central_only", "easy", [], "colloquial_phrasing", "What are the legal remedies if an employer fails to disburse final salary settlement and holding PF?")
add_q("p24-diff-002", "what are rules for 144 accessible pdf under hindu act 1955?", "Family Law", False, "central_only", "moderately_ambiguous", [], "wrong_act_or_title_cited", "What are statutory divorce rules under Hindu Marriage Act 1955?")
add_q("p24-diff-003", "Is cryptocurency illegal in india and penalised under reserve bank act?", "Banking & Finance", False, "central_only", "moderately_ambiguous", [], "misspelling_and_vague", "What is the legal status and tax governance of cryptocurrency trading in India?")
add_q("p24-diff-004", "Can I return food ordered on Swiggy if delivery was late by 2 hours?", "Consumer Protection", False, "central_only", "no_evidence_expected", [], "no_evidence_in_corpus")
add_q("p24-diff-005", "What is shop opening time in my city?", "Employment & Labour", False, "jurisdiction_ambiguous", "clarification_required", [], "missing_jurisdiction")
add_q("p24-diff-006", "I bought stolen phone from street seller without knowing, will police arrest me?", "Criminal Law", False, "central_only", "multi_concept", [], "multi_concept_mixing")
add_q("p24-diff-007", "What did Supreme Court rule in Kesavananda Bharati case regarding fundamental rights?", "Constitutional Rights", False, "central_only", "judgment_focused", [], "named_entity_search")
add_q("p24-diff-008", "Can apartment association prohibit pets in flats legally?", "Property Law", False, "jurisdiction_ambiguous", "mixed_legislation_judgment", [], "vague_layman_wording")
add_q("p24-diff-009", "What is legal process for Lok Adalat compromise decree enforcement?", "Constitutional Rights", True, "central_only", "legislation_focused", ["procedure"], "procedural_legal_aid")

# Write output file
with open(out_file, "w", encoding="utf-8") as f:
    for q in queries:
        f.write(json.dumps(q, ensure_ascii=False) + "\n")

print(f"Successfully generated {len(queries)} queries in {out_file}")
