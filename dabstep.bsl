# ============================================================
# DABstep — Payment Processing Domain Model (BSL).
# Built strictly from adyen/DABstep data/context/* prior to viewing tasks.
# Architecture (Option B — Hybrid / VKG-ready):
#   - Full domain ontology + reference data + 30 Merchants + 1,000 FeeRules
#     + 60 MonthlyMerchantStats live as individuals in the BOLDSEA graph.
#   - Payment (138,236 rows in payments.csv) lives in the graph as Model Payment
#     plus ExternalDataset metadata, backed by payments_provider.py (SQLite).
# ============================================================

# ---------- 1. Concepts ----------
Concept: Individual: Country
Concept: Individual: CardScheme
Concept: Individual: AccountType
Concept: Individual: ACI
Concept: Individual: Acquirer
Concept: Individual: MerchantCategoryCode
Concept: Individual: Merchant
Concept: Individual: FeeRule
Concept: Individual: MonthlyMerchantStats
Concept: Individual: Payment
Concept: Individual: PaymentGroup
Concept: Individual: ExternalDataset
Concept: Individual: DomainPolicy

# ---------- 2. Global Properties ----------
# Reference & descriptor attributes
Attribute: Individual: isoCode
: DataType: String
Attribute: Individual: codeLabel
: DataType: String
Attribute: Individual: mccCode
: DataType: Integer
Attribute: Individual: summary
: DataType: String

# Merchant attributes
Attribute: Individual: captureDelayRaw
: DataType: String
Attribute: Individual: captureDelayBucket
: DataType: String
Attribute: Individual: annualTxCount
: DataType: Integer
Attribute: Individual: annualVolume
: DataType: Numeric
: Unit: EUR
Attribute: Individual: annualFraudVolume
: DataType: Numeric
: Unit: EUR
Attribute: Individual: annualFraudRate
: DataType: Numeric
Attribute: Individual: exceedsFraudThreshold
: DataType: Boolean

# DomainPolicy attributes (manual.md operational rules, limits, fines, glossary, contacts)
Attribute: Individual: policyCategory
: DataType: EnumType
: AttributeValue: security
: AttributeValue: compliance
: AttributeValue: pricing
: AttributeValue: fraud
: AttributeValue: settlement
: AttributeValue: glossary
: AttributeValue: support
Attribute: Individual: metricName
: DataType: String
Attribute: Individual: numericValue
: DataType: Numeric
Attribute: Individual: minNumericValue
: DataType: Numeric
Attribute: Individual: maxNumericValue
: DataType: Numeric
Attribute: Individual: unitLabel
: DataType: String
Attribute: Individual: formulaText
: DataType: String
Attribute: Individual: manualSection
: DataType: String

# FeeRule attributes
Attribute: Individual: ruleId
: DataType: Integer
Attribute: Individual: captureDelayRule
: DataType: EnumType
: AttributeValue: manual
: AttributeValue: immediate
: AttributeValue: <3
: AttributeValue: 3-5
: AttributeValue: >5
Attribute: Individual: monthlyFraudLevelRule
: DataType: EnumType
: AttributeValue: <7.2%
: AttributeValue: 7.2%-7.7%
: AttributeValue: 7.7%-8.3%
: AttributeValue: >8.3%
Attribute: Individual: monthlyVolumeRule
: DataType: EnumType
: AttributeValue: <100k
: AttributeValue: 100k-1m
: AttributeValue: 1m-5m
: AttributeValue: >5m
Attribute: Individual: isCreditRule
: DataType: Boolean
Attribute: Individual: intracountryRule
: DataType: Boolean
Attribute: Individual: fixedAmount
: DataType: Numeric
: Unit: EUR
Attribute: Individual: feeRate
: DataType: Integer

# MonthlyMerchantStats attributes
Attribute: Individual: txYear
: DataType: Integer
Attribute: Individual: txMonth
: DataType: Integer
Attribute: Individual: txCount
: DataType: Integer
Attribute: Individual: totalVolume
: DataType: Numeric
: Unit: EUR
Attribute: Individual: fraudTxCount
: DataType: Integer
Attribute: Individual: fraudVolume
: DataType: Numeric
: Unit: EUR
Attribute: Individual: refusedTxCount
: DataType: Integer
Attribute: Individual: fraudRate
: DataType: Numeric
Attribute: Individual: volumeBucket
: DataType: String
Attribute: Individual: fraudBucket
: DataType: String

# Payment (virtualized fact model) attributes
Attribute: Individual: pspReference
: DataType: String
Attribute: Individual: dayOfYear
: DataType: Integer
Attribute: Individual: hourOfDay
: DataType: Integer
Attribute: Individual: minuteOfHour
: DataType: Integer
Attribute: Individual: isCredit
: DataType: Boolean
Attribute: Individual: eurAmount
: DataType: Numeric
: Unit: EUR
Attribute: Individual: deviceType
: DataType: EnumType
: AttributeValue: Windows
: AttributeValue: Linux
: AttributeValue: MacOS
: AttributeValue: iOS
: AttributeValue: Android
: AttributeValue: Other
Attribute: Individual: ipAddressHash
: DataType: String
Attribute: Individual: emailAddressHash
: DataType: String
Attribute: Individual: cardNumberHash
: DataType: String
Attribute: Individual: shopperInteraction
: DataType: EnumType
: AttributeValue: Ecommerce
: AttributeValue: POS
Attribute: Individual: cardBin
: DataType: String
Attribute: Individual: hasFraudulentDispute
: DataType: Boolean
Attribute: Individual: isRefusedByAdyen
: DataType: Boolean
Attribute: Individual: isIntracountry
: DataType: Boolean
Attribute: Individual: calculatedFee
: DataType: Numeric
: Unit: EUR

# ExternalDataset metadata attributes
Attribute: Individual: targetModelName
: DataType: String
Attribute: Individual: sourcePath
: DataType: String
Attribute: Individual: sqlitePath
: DataType: String
Attribute: Individual: providerScript
: DataType: String
Attribute: Individual: rowCount
: DataType: Integer

# Relations
Relation: Individual: country
: Range: Country
Relation: Individual: acquirers
: Range: Acquirer
: Multiple: 1
Relation: Individual: mcc
: Range: MerchantCategoryCode
Relation: Individual: mccs
: Range: MerchantCategoryCode
: Multiple: 1
Relation: Individual: accountType
: Range: AccountType
Relation: Individual: accountTypes
: Range: AccountType
: Multiple: 1
Relation: Individual: cardScheme
: Range: CardScheme
Relation: Individual: aci
: Range: ACI
Relation: Individual: acis
: Range: ACI
: Multiple: 1
Relation: Individual: merchant
: Range: Merchant
Relation: Individual: ipCountry
: Range: Country
Relation: Individual: issuingCountry
: Range: Country
Relation: Individual: acquirerCountry
: Range: Country
Relation: Individual: feeGroup
: Range: PaymentGroup
Relation: Individual: monthStats
: Range: MonthlyMerchantStats
Relation: Individual: matchedFeeRules
: Range: FeeRule
: Multiple: 1

# ---------- 3. Vocabulary ----------
Vocabulary: Individual: DABstepVocabulary
: Model: Model_Vocabulary
: Attributes: isoCode
: Attributes: codeLabel
: Attributes: mccCode
: Attributes: summary
: Attributes: captureDelayRaw
: Attributes: captureDelayBucket
: Attributes: annualTxCount
: Attributes: annualVolume
: Attributes: annualFraudVolume
: Attributes: annualFraudRate
: Attributes: exceedsFraudThreshold
: Attributes: policyCategory
: Attributes: metricName
: Attributes: numericValue
: Attributes: minNumericValue
: Attributes: maxNumericValue
: Attributes: unitLabel
: Attributes: formulaText
: Attributes: manualSection
: Attributes: ruleId
: Attributes: captureDelayRule
: Attributes: monthlyFraudLevelRule
: Attributes: monthlyVolumeRule
: Attributes: isCreditRule
: Attributes: intracountryRule
: Attributes: fixedAmount
: Attributes: feeRate
: Attributes: txYear
: Attributes: txMonth
: Attributes: txCount
: Attributes: totalVolume
: Attributes: fraudTxCount
: Attributes: fraudVolume
: Attributes: refusedTxCount
: Attributes: fraudRate
: Attributes: volumeBucket
: Attributes: fraudBucket
: Attributes: pspReference
: Attributes: dayOfYear
: Attributes: hourOfDay
: Attributes: minuteOfHour
: Attributes: isCredit
: Attributes: eurAmount
: Attributes: deviceType
: Attributes: ipAddressHash
: Attributes: emailAddressHash
: Attributes: cardNumberHash
: Attributes: shopperInteraction
: Attributes: cardBin
: Attributes: hasFraudulentDispute
: Attributes: isRefusedByAdyen
: Attributes: isIntracountry
: Attributes: calculatedFee
: Attributes: targetModelName
: Attributes: sourcePath
: Attributes: sqlitePath
: Attributes: providerScript
: Attributes: rowCount
: Relations: country
: Relations: acquirers
: Relations: mcc
: Relations: mccs
: Relations: accountType
: Relations: accountTypes
: Relations: cardScheme
: Relations: aci
: Relations: acis
: Relations: merchant
: Relations: ipCountry
: Relations: issuingCountry
: Relations: acquirerCountry
: Relations: feeGroup
: Relations: monthStats
: Relations: matchedFeeRules

# ---------- 4. Domain Models ----------
Country: Model: Model Country
: Attribute: isoCode
:: Required: 1
: Attribute: summary

CardScheme: Model: Model CardScheme
: Attribute: summary

AccountType: Model: Model AccountType
: Attribute: codeLabel
:: Required: 1
: Attribute: summary

ACI: Model: Model ACI
: Attribute: codeLabel
:: Required: 1
: Attribute: summary

Acquirer: Model: Model Acquirer
: Relation: country
:: Required: 1

MerchantCategoryCode: Model: Model MCC
: Attribute: mccCode
:: Required: 1
: Attribute: summary

Merchant: Model: Model Merchant
: Attribute: captureDelayRaw
:: Required: 1
: Attribute: captureDelayBucket
:: SetValue: IsUndefined($$.captureDelayRaw) ? undefined : ($$.captureDelayRaw == "manual" ? "manual" : ($$.captureDelayRaw == "immediate" ? "immediate" : (($$.captureDelayRaw == "1" || $$.captureDelayRaw == "2") ? "<3" : (($$.captureDelayRaw == "3" || $$.captureDelayRaw == "4" || $$.captureDelayRaw == "5") ? "3-5" : ">5"))))
: Relation: acquirers
:: Multiple: 1
: Relation: mcc
:: Required: 1
: Relation: accountType
:: Required: 1
: Attribute: annualTxCount
:: SetValue: Coalesce(Sum(Map($($Base == "MonthlyMerchantStats", merchant == $CurrentIndividual), $$It.txCount)), 0)
: Attribute: annualVolume
:: SetValue: Coalesce(Sum(Map($($Base == "MonthlyMerchantStats", merchant == $CurrentIndividual), $$It.totalVolume)), 0)
: Attribute: annualFraudVolume
:: SetValue: Coalesce(Sum(Map($($Base == "MonthlyMerchantStats", merchant == $CurrentIndividual), $$It.fraudVolume)), 0)
: Attribute: annualFraudRate
:: SetValue: IsUndefined($$.annualVolume) ? undefined : ($$.annualVolume > 0 ? $$.annualFraudVolume / $$.annualVolume : 0)
# Applicability boundary: the threshold is a fact of DomainPolicy. While manual.md gives no number
# the policy has no numericValue and this value does not exist (Not Applicable), neither true nor false.
: Attribute: exceedsFraudThreshold
:: SetValue: IsDefined(First(@("Policy-ExcessiveFraudThreshold").numericValue)) ? $$.annualFraudRate > First(@("Policy-ExcessiveFraudThreshold").numericValue) : undefined

DomainPolicy: Model: Model DomainPolicy
: Attribute: policyCategory
:: Required: 1
: Attribute: metricName
:: Required: 1
: Attribute: numericValue
: Attribute: minNumericValue
: Attribute: maxNumericValue
: Attribute: unitLabel
: Attribute: formulaText
: Attribute: manualSection
: Attribute: summary
:: Required: 1

FeeRule: Model: Model FeeRule
: Attribute: ruleId
:: Required: 1
: Relation: cardScheme
:: Required: 1
: Relation: accountTypes
:: Multiple: 1
: Attribute: captureDelayRule
: Attribute: monthlyFraudLevelRule
: Attribute: monthlyVolumeRule
: Relation: mccs
:: Multiple: 1
: Attribute: isCreditRule
: Relation: acis
:: Multiple: 1
: Attribute: intracountryRule
: Attribute: fixedAmount
:: Required: 1
: Attribute: feeRate
:: Required: 1

MonthlyMerchantStats: Model: Model MonthlyMerchantStats
: Relation: merchant
:: Required: 1
: Attribute: txYear
:: Required: 1
: Attribute: txMonth
:: Required: 1
:: ValueCondition: $Input >= 1 && $Input <= 12
: Attribute: txCount
:: Required: 1
: Attribute: totalVolume
:: Required: 1
: Attribute: fraudTxCount
:: Required: 1
: Attribute: fraudVolume
:: Required: 1
: Attribute: refusedTxCount
:: Required: 1
: Attribute: fraudRate
:: SetValue: IsUndefined($$.totalVolume) ? undefined : ($$.totalVolume > 0 ? $$.fraudVolume / $$.totalVolume : 0)
: Attribute: volumeBucket
:: SetValue: IsUndefined($$.totalVolume) ? undefined : ($$.totalVolume < 100000 ? "<100k" : ($$.totalVolume <= 1000000 ? "100k-1m" : ($$.totalVolume <= 5000000 ? "1m-5m" : ">5m")))
: Attribute: fraudBucket
:: SetValue: IsUndefined($$.fraudRate) ? undefined : ($$.fraudRate < 0.072 ? "<7.2%" : ($$.fraudRate <= 0.077 ? "7.2%-7.7%" : ($$.fraudRate <= 0.083 ? "7.7%-8.3%" : ">8.3%")))

# Virtualized fact model for payments.csv (138,236 rows served by payments_provider.py)
Payment: Model: Model Payment
: Attribute: pspReference
:: Required: 1
: Relation: merchant
:: Required: 1
: Relation: cardScheme
:: Required: 1
: Attribute: txYear
:: Required: 1
: Attribute: dayOfYear
:: Required: 1
:: ValueCondition: $Input >= 1 && $Input <= 366
: Attribute: txMonth
:: SetValue: IsUndefined($$.dayOfYear) ? undefined : ($$.dayOfYear <= 31 ? 1 : ($$.dayOfYear <= 59 ? 2 : ($$.dayOfYear <= 90 ? 3 : ($$.dayOfYear <= 120 ? 4 : ($$.dayOfYear <= 151 ? 5 : ($$.dayOfYear <= 181 ? 6 : ($$.dayOfYear <= 212 ? 7 : ($$.dayOfYear <= 243 ? 8 : ($$.dayOfYear <= 273 ? 9 : ($$.dayOfYear <= 304 ? 10 : ($$.dayOfYear <= 334 ? 11 : 12)))))))))))
: Attribute: hourOfDay
: Attribute: minuteOfHour
: Attribute: isCredit
: Attribute: eurAmount
:: Required: 1
: Relation: ipCountry
: Relation: issuingCountry
: Relation: acquirerCountry
: Attribute: isIntracountry
:: SetValue: (IsUndefined($$.issuingCountry) || IsUndefined($$.acquirerCountry)) ? undefined : ($$.issuingCountry == $$.acquirerCountry)
: Attribute: deviceType
: Attribute: ipAddressHash
: Attribute: emailAddressHash
: Attribute: cardNumberHash
: Attribute: shopperInteraction
: Attribute: cardBin
: Attribute: hasFraudulentDispute
: Attribute: isRefusedByAdyen
: Relation: aci
# Fee-relevant group the payment belongs to; matching is defined once, in Model PaymentGroup
: Relation: feeGroup
:: SetValue: First($($Model == "Model PaymentGroup", merchant == $$.merchant, cardScheme == $$.cardScheme, txYear == $$.txYear, txMonth == $$.txMonth, isCredit == $$.isCredit, aci == $$.aci, isIntracountry == $$.isIntracountry))
: Relation: matchedFeeRules
:: Multiple: 1
:: SetValue: @@.feeGroup.matchedFeeRules
# Fee = sum over all matched rules; no matched rule -> no value (unknown, not zero)
: Attribute: calculatedFee
:: SetValue: Sum(@@.matchedFeeRules.fixedAmount) + Sum(@@.matchedFeeRules.feeRate) * $$.eurAmount / 10000

# All payments sharing the attributes fee rules look at: one group per
# merchant x card scheme x month x credit x ACI x intracountry (4,363 groups cover payments.csv).
# txCount / totalVolume are aggregates supplied by the payments provider; the rest is derived.
PaymentGroup: Model: Model PaymentGroup
: Relation: merchant
:: Required: 1
: Relation: cardScheme
:: Required: 1
: Attribute: txYear
:: Required: 1
: Attribute: txMonth
:: Required: 1
: Attribute: isCredit
:: Required: 1
: Relation: aci
:: Required: 1
: Attribute: isIntracountry
:: Required: 1
: Attribute: txCount
:: Required: 1
: Attribute: totalVolume
:: Required: 1
# Monthly merchant aggregate the group falls into (source of fraud / volume buckets)
: Relation: monthStats
:: SetValue: First($($Model == "Model MonthlyMerchantStats", merchant == $$.merchant, txYear == $$.txYear, txMonth == $$.txMonth))
# FeeRule matching (manual.md §5): an empty list / absent attribute of a rule is a wildcard
: Relation: matchedFeeRules
:: Multiple: 1
:: SetValue: $($Model == "Model FeeRule", cardScheme == $$.cardScheme, Count($$It.accountTypes) == 0 || accountTypes == @@.merchant.accountType, IsUndefined($$It.captureDelayRule) == true || captureDelayRule == @@.merchant.captureDelayBucket, IsUndefined($$It.monthlyFraudLevelRule) == true || monthlyFraudLevelRule == @@.monthStats.fraudBucket, IsUndefined($$It.monthlyVolumeRule) == true || monthlyVolumeRule == @@.monthStats.volumeBucket, Count($$It.mccs) == 0 || mccs == @@.merchant.mcc, IsUndefined($$It.isCreditRule) == true || isCreditRule == $$.isCredit, Count($$It.acis) == 0 || acis == $$.aci, IsUndefined($$It.intracountryRule) == true || intracountryRule == $$.isIntracountry)
# Group fee = sum over all matched rules; no matched rule -> no value (unknown, not zero)
: Attribute: calculatedFee
:: SetValue: Sum(@@.matchedFeeRules.fixedAmount) * $$.txCount + Sum(@@.matchedFeeRules.feeRate) * $$.totalVolume / 10000

ExternalDataset: Model: Model ExternalDataset
: Attribute: targetModelName
:: Required: 1
: Attribute: sourcePath
:: Required: 1
: Attribute: sqlitePath
: Attribute: providerScript
: Attribute: rowCount

# ---------- 5. External Dataset Registry ----------
ExternalDataset: Individual: PaymentsDataset
: Model: Model ExternalDataset
: targetModelName: Model Payment
: sourcePath: applications/dabstep/data/context/payments.csv
: sqlitePath: applications/dabstep/data/payments.sqlite
: providerScript: applications/dabstep/payments_provider.py
: rowCount: 138236

# ---------- 6. Views ----------
View: Individual: Merchant List
: Model: View List
: ViewConcept: Merchant
:: ViewMode: table
:: ViewQuery: $($Model == "Model Merchant")
::: Visibility: hide
:: Include: accountType
:: Include: mcc
:: Include: captureDelayRaw
:: Include: captureDelayBucket
:: Include: acquirers

View: Individual: Merchant Card
: Model: View Individual
: ConceptPage: Merchant

View: Individual: Monthly Stats List
: Model: View List
: ViewConcept: MonthlyMerchantStats
:: ViewMode: table
:: ViewQuery: $($Model == "Model MonthlyMerchantStats")
::: Visibility: hide
:: Include: merchant
:: Include: txMonth
:: Include: txCount
:: Include: totalVolume
:: Include: fraudRate
:: Include: volumeBucket
:: Include: fraudBucket

View: Individual: Monthly Stats Card
: Model: View Individual
: ConceptPage: MonthlyMerchantStats

View: Individual: FeeRule List
: Model: View List
: ViewConcept: FeeRule
:: ViewMode: table
:: ViewQuery: $($Model == "Model FeeRule")
::: Visibility: hide
:: Include: ruleId
:: Include: cardScheme
:: Include: fixedAmount
:: Include: feeRate
:: Include: isCreditRule
:: Include: intracountryRule
:: Include: captureDelayRule
:: Include: monthlyVolumeRule
:: Include: monthlyFraudLevelRule

View: Individual: FeeRule Card
: Model: View Individual
: ConceptPage: FeeRule

View: Individual: External Dataset Card
: Model: View Individual
: ViewIndividual: PaymentsDataset
: ConceptPage: ExternalDataset

View: Individual: DABstep Menu
: Model: View Individual
: ViewLink: Merchant List
:: LinkType: link
:: Title: Merchants
: ViewLink: Monthly Stats List
:: LinkType: link
:: Title: Monthly Stats
: ViewLink: FeeRule List
:: LinkType: link
:: Title: Fee Rules
: ViewLink: External Dataset Card
:: LinkType: link
:: Title: Payments Dataset

View: Individual: Blank
: Model: View Individual

View: Individual: DABstep Layout
: Model: View Layout
: application: DABstepApp
: ViewIndividual: DABstep Menu
: ViewIndividual: Merchant List
: ViewIndividual: Merchant Card
: ViewIndividual: Monthly Stats List
: ViewIndividual: Monthly Stats Card
: ViewIndividual: FeeRule List
: ViewIndividual: FeeRule Card
: ViewIndividual: External Dataset Card
: ViewIndividual: Blank
: Slot: header
:: Format: top 40px
:: Content: DABstep Menu
:: TargetSlot: list
:: NoHeader: 1
: Slot: list
:: Format: left 3fr
:: Content: Merchant List
:: DefaultContent: Merchant List
:: DefaultContent: Monthly Stats List
:: DefaultContent: FeeRule List
:: DefaultContent: External Dataset Card
:: TargetSlot: card
: Slot: card
:: Format: right 2fr
:: Content: Blank
:: DefaultContent: Blank
:: DefaultContent: Merchant Card
:: DefaultContent: Monthly Stats Card
:: DefaultContent: FeeRule Card
:: DefaultContent: External Dataset Card
:: Title: Details

# ---------- 7. Application and SPA State ----------
Application: Individual: DABstepApp
: Model: Model_Application
: Models: Model SPA State
: Models: Model Country
: Models: Model CardScheme
: Models: Model AccountType
: Models: Model ACI
: Models: Model Acquirer
: Models: Model MCC
: Models: Model Merchant
: Models: Model FeeRule
: Models: Model MonthlyMerchantStats
: Models: Model Payment
: Models: Model PaymentGroup
: Models: Model ExternalDataset
: Models: Model DomainPolicy
: Vocabularies: DABstepVocabulary
: layouts: DABstep Layout
: lastLayout: DABstep Layout

SPAState: Individual: SPA State
: Model: Model SPA State
: currentLayout: DABstep Layout
