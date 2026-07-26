import type { ActionRequired, Answer } from '../api/client'

/** Shaped from the live API's response to `?q=wool`; not invented copy. */
export const woolAnswer: Answer = {
  id: 'FTA-005',
  topic: 'Wool',
  sector: 'Agriculture',
  treatment: 'Tariff eliminated day one.',
  confirmed: true,
  citation: 'MFAT National Interest Analysis, key tariff outcomes table',
  verified_at: '2026-07-22',
  status_line:
    'NZ-India FTA signed 27 April 2026 (negotiations concluded 22 Dec 2025). Not yet in force - awaiting domestic ratification in both countries. Benefits are agreed, applying once the FTA enters into force, not current access.',
  jurisdiction: 'New Zealand-India',
  next_step:
    "Confirm the exact tariff line in the FTA's Annex 2A schedule, or contact INZBC for product-specific guidance.",
  disclaimer:
    'This response has been prepared using official government publications and trusted industry sources maintained by the India New Zealand Business Council (INZBC). Where an answer cannot be verified from authoritative sources, INZBC will indicate this rather than speculate.',
  confidence: 'High',
  confidence_meaning: 'Verified using official government or treaty sources.',
  notes: null,
}

export const escalation: ActionRequired = {
  message:
    'INZBC does not hold a verified answer to this question in its FTA source corpus. Rather than provide an unverified answer, this query is referred to INZBC.',
  next_step:
    "Check the exact tariff line in the FTA's Annex 2A schedule, or raise an enquiry with INZBC.",
  escalation_path:
    'Raise an enquiry with INZBC for product-specific guidance. Where a decision is time-critical, contact the relevant government agency or a qualified professional adviser directly.',
  status_line: woolAnswer.status_line,
  jurisdiction: 'New Zealand-India',
  disclaimer: woolAnswer.disclaimer,
  confidence: 'Action Required',
  confidence_meaning:
    'INZBC recommends contacting the relevant government agency or seeking professional advice before proceeding.',
}
