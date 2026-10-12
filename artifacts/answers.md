# Answers

Generated from reconciliation run 1 (extraction version `fixture`, 31 documents reconciled, 0 not extracted). Full structured results: `answers.json`.

## DEV-01

> For January 5–30, 2026, how many therapy sessions did Rowan attend, by service type and in total, and on how many distinct days? Provide a reviewable abstraction with source support and explain records that could lead to duplicate or ineligible counts.

**12 therapy sessions** (family 2, group 5, individual 5) on **11 distinct days**, 585-595 minutes.

| Encounter | Date | Service | Minutes | Basis | Sources |
|---|---|---|---|---|---|
| HG-E101 | 2026-01-05 | individual_therapy | 50 | 09:00-09:50 (50) = 50 min | early_appointment_status_export.txt, intake_and_individual_jan05.txt |
| HG-E102 | 2026-01-06 | group_therapy | 45 | 10:15-11:15 (60) - breaks 10:45-11:00 (15) = 45 min | early_appointment_status_export.txt, early_group_attendance_roster.txt, group_facilitator_jan06.txt |
| HG-E104 | 2026-01-09 | family_therapy | 45 | 14:00-14:45 (45) = 45 min | early_appointment_status_export.txt, family_cofacilitator_jan09.txt, family_primary_jan09.txt |
| HG-E105 | 2026-01-12 | group_therapy | 75 | 10:00-11:30 (90) - breaks 10:40-10:55 (15) = 75 min | early_appointment_status_export.txt, early_group_attendance_roster.txt, group_facilitator_jan12.txt |
| HG-E107 | 2026-01-14 | individual_therapy | 45 | 11:00-11:45 (45) = 45 min | early_appointment_status_export.txt, individual_therapy_jan14.txt |
| HG-E110 | 2026-01-19 | group_therapy | 60 | 10:00-11:15 (75) - breaks 10:45-11:00 (15) = 60 min | BH-D101_group_content_2026-01-19.txt, BH-D102_original_attendance_2026-01-19.txt, BH-D103_attendance_correction_2026-01-20.txt, BH-D104_resent_roster_received_2026-01-26.txt |
| HG-E111 | 2026-01-19 | individual_therapy | 30 | 11:15-11:45 (30) = 30 min | BH-D105_individual_2026-01-19.txt |
| HG-E112 | 2026-01-21 | individual_therapy | 45 | 13:00-13:20 (20) + 13:30-13:55 (25) = 45 min | BH-D106_telehealth_2026-01-21.txt |
| HG-E113 | 2026-01-22 | group_therapy | 45 | 10:30-11:30 (60) - breaks 10:45-11:00 (15) = 45 min | BH-D107_group_activity_records_2026-01-22_and_29.txt, BH-D108_final_attendance_and_cancellation_register.txt |
| HG-E115 | 2026-01-26 | individual_therapy | 40-50 | 09:10-09:50 (40) = 40 min<br>09:00-09:50 (50) = 50 min | BH-D110_individual_primary_record_2026-01-26.txt, BH-D111_individual_second_record_2026-01-26.txt |
| HG-E118 | 2026-01-29 | group_therapy | 75 | 10:00-11:30 (90) - breaks 10:45-11:00 (15) = 75 min | BH-D107_group_activity_records_2026-01-22_and_29.txt, BH-D108_final_attendance_and_cancellation_register.txt |
| HG-E119 | 2026-01-30 | family_therapy | 30 | 13:15-13:45 (30) = 30 min | BH-D113_family_therapy_2026-01-30.txt |

Encounters documented by several sources are counted once; their sources are listed together.

**Excluded:**
- HG-E103 (2026-01-08, individual_therapy): no show. Sources: early_appointment_status_export.txt, missed_visit_outreach_jan08.txt
- HG-E106 (2026-01-13, medication_management): medication management is not an eligible therapy service. Sources: early_appointment_status_export.txt, medication_review_jan13.txt
- HG-E108 (2026-01-15, group_therapy): cancelled by clinic. Sources: early_appointment_status_export.txt, group_cancellation_notice_jan15.txt
- HG-E109 (2026-01-16, collateral_contact): collateral contact is not an eligible therapy service. Sources: early_appointment_status_export.txt, partner_collateral_jan16.txt
- HG-E114 (2026-01-23, care_coordination): care coordination is not an eligible therapy service. Sources: BH-D109_care_coordination_2026-01-23.txt
- HG-E116 (2026-01-27, group_therapy): no show. Sources: BH-D108_final_attendance_and_cancellation_register.txt, BH-D112_draft_note_and_charge_extract_2026-01-27.txt
- HG-E117 (2026-01-28, individual_therapy): cancelled by patient. Sources: BH-D108_final_attendance_and_cancellation_register.txt
- HG-E120 (2026-01-30, medication_management): medication management is not an eligible therapy service. Sources: BH-D114_medication_management_2026-01-30.txt

## DEV-02

> How many therapy minutes and hours did Rowan actually receive during the review period, overall and for each Monday–Sunday week? Show calculations or supporting detail, and report any conclusion the available documents do not settle.

**585-595 minutes** (9.75-9.92 hours).

| Week of | Period | Minutes | Encounters |
|---|---|---|---|
| 2026-01-05 | 2026-01-05 to 2026-01-11 | 140 | HG-E101 (50), HG-E102 (45), HG-E104 (45) |
| 2026-01-12 | 2026-01-12 to 2026-01-18 | 120 | HG-E105 (75), HG-E107 (45) |
| 2026-01-19 | 2026-01-19 to 2026-01-25 | 180 | HG-E110 (60), HG-E111 (30), HG-E112 (45), HG-E113 (45) |
| 2026-01-26 | 2026-01-26 to 2026-01-30 (partial) | 145-155 | HG-E115 (40-50), HG-E118 (75), HG-E119 (30) |

**Not settled by the record:**
- HG-E115 (2026-01-26): 40-50 minutes, disputed. Alternatives: 09:10-09:50 (40) = 40 min | 09:00-09:50 (50) = 50 min. Sources: BH-D110_individual_primary_record_2026-01-26.txt, BH-D111_individual_second_record_2026-01-26.txt

## DEV-03

> For each week, did the delivered therapy meet the goal documented in Rowan’s treatment plan? State the goal, the relevant therapy-day and minute totals, and whether it was met, not met, or cannot be determined from the current record.

**Goal** (2026-01-05 to 2026-01-30): at least 3 therapy days and 150 minutes per Monday-Sunday week; counted services: family_therapy, group_therapy, individual_therapy. Source: "Episode dates: 2026-01-05 through 2026-01-30"; "Local treatment participation goal: at least 3 therapy days and at least 150 minutes of patient-present therapy in each Monday–Sunday week."; "Patient-present individual, group, and family therapy contribute to the minute goal."

| Week of | Period | Therapy days | Minutes | Result | Depends on |
|---|---|---|---|---|---|
| 2026-01-05 | 2026-01-05 to 2026-01-11 | 3 | 140 | not_met |  |
| 2026-01-12 | 2026-01-12 to 2026-01-18 | 2 | 120 | not_met |  |
| 2026-01-19 | 2026-01-19 to 2026-01-25 | 3 | 180 | met |  |
| 2026-01-26 | 2026-01-26 to 2026-01-30 | 3 | 145-155 | cannot_determine | HG-E115 |

Consecutive weeks below goal: definite [['2026-01-05', '2026-01-12']]; dependent on unresolved documentation none.

## DEV-04

> Reconstruct the care on January 19 and January 21. How many therapy contacts and patient therapy minutes occurred on each date, and how do the attendance records, clinical notes, later documents, and telehealth records affect your answer?

### 2026-01-19: 2 therapy contact(s), 90 minutes

**HG-E110** (group_therapy, included: patient attended eligible therapy); duration corrected: 10:00-11:15 (75) - breaks 10:45-11:00 (15) = 60 min
- accepted: attendance attendance=attended [final, authored 2026-01-19] "Rowan initially followed the exercise and identified postponing a message to a supervisor as a familiar pattern." (BH-D101_group_content_2026-01-19.txt 855-967)
- accepted: attendance attendance=attended [final, authored 2026-01-19] "Patient arrival: 10:00 | Patient departure: 11:30 | Status: Attended" (BH-D102_original_attendance_2026-01-19.txt 296-364)
- accepted: attendance attendance=attended [final, authored 2026-01-19] "Patient arrival: 10:00 | Patient departure: 11:30 | Status: Attended" (BH-D104_resent_roster_received_2026-01-26.txt 789-857)
- accepted: break starts_at=2026-01-19T10:45, ends_at=2026-01-19T11:00 [final, authored 2026-01-19] "Nontherapeutic break: 10:45–11:00." (BH-D101_group_content_2026-01-19.txt 261-295)
- applied_correction (applied to 2 claim(s)): correction corrected_field=presence_end, replaced_value=2026-01-19T11:30, replacement_value=2026-01-19T11:15 [final, authored 2026-01-20] "Correction: Patient departure for HG-E110 is 11:15, replacing the original roster value of 11:30. Patient arrival remains 10:00." (BH-D103_attendance_correction_2026-01-20.txt 223-351)
- accepted: encounter_detail service_date=2026-01-19, service_type=group_therapy [final, authored 2026-01-19] "Skills group clinical record | Service date: January 19, 2026" (BH-D101_group_content_2026-01-19.txt 52-113); "Group encounter: HG-E110" (BH-D101_group_content_2026-01-19.txt 114-138)
- accepted: encounter_detail service_date=2026-01-19, service_type=group_therapy [final, authored 2026-01-19] "Service date: January 19, 2026 | Group encounter: HG-E110" (BH-D102_original_attendance_2026-01-19.txt 95-152)
- accepted: encounter_detail service_date=2026-01-19, service_type=group_therapy [final, authored 2026-01-19] "Service date: January 19, 2026 | Group encounter: HG-E110" (BH-D104_resent_roster_received_2026-01-26.txt 644-701)
- corrected (presence_end 11:30 -> 11:15): presence starts_at=2026-01-19T10:00, ends_at=2026-01-19T11:30 [final, authored 2026-01-19] "Patient arrival: 10:00 | Patient departure: 11:30 | Status: Attended" (BH-D102_original_attendance_2026-01-19.txt 296-364)
- corrected (presence_end 11:30 -> 11:15): presence starts_at=2026-01-19T10:00, ends_at=2026-01-19T11:30 [final, authored 2026-01-19] "Patient arrival: 10:00 | Patient departure: 11:30 | Status: Attended" (BH-D104_resent_roster_received_2026-01-26.txt 789-857); "Original signature: Leah Chen, LCSW | January 19, 2026, 12:14" (BH-D104_resent_roster_received_2026-01-26.txt 858-919)

**HG-E111** (individual_therapy, included: patient attended eligible therapy); duration established: 11:15-11:45 (30) = 30 min
- accepted: attendance attendance=attended [final, authored 2026-01-19] "Rowan participated throughout the individual contact" (BH-D105_individual_2026-01-19.txt 793-845)
- accepted: encounter_detail service_date=2026-01-19, service_type=individual_therapy [final, authored 2026-01-19] "Individual psychotherapy | Encounter HG-E111" (BH-D105_individual_2026-01-19.txt 52-96); "January 19, 2026 | In person" (BH-D105_individual_2026-01-19.txt 143-171)
- accepted: presence starts_at=2026-01-19T11:15, ends_at=2026-01-19T11:45 [final, authored 2026-01-19] "Patient contact: 11:15–11:45 | Completed: 30 minutes" (BH-D105_individual_2026-01-19.txt 172-224)

### 2026-01-21: 1 therapy contact(s), 45 minutes

**HG-E112** (individual_therapy, included: patient attended eligible therapy); duration established: 13:00-13:20 (20) + 13:30-13:55 (25) = 45 min
- accepted: attendance attendance=attended [final, authored 2026-01-21] "Rowan was engaged and able to restate the agreed task." (BH-D106_telehealth_2026-01-21.txt 1163-1217)
- accepted: break starts_at=2026-01-21T13:20, ends_at=2026-01-21T13:30 [final, authored 2026-01-21] "Connection was lost from 13:20–13:30; there was no therapeutic contact during that interval." (BH-D106_telehealth_2026-01-21.txt 275-367)
- accepted: encounter_detail service_date=2026-01-21, service_type=individual_therapy [final, authored 2026-01-21] "Individual psychotherapy | Encounter HG-E112 | Appointment HG-A112" (BH-D106_telehealth_2026-01-21.txt 52-118); "January 21, 2026 | Video" (BH-D106_telehealth_2026-01-21.txt 165-189)
- disputed: presence starts_at=2026-01-21T13:00, ends_at=2026-01-21T13:20 [final, authored 2026-01-21] "Patient contact occurred 13:00–13:20 and 13:30–13:55." (BH-D106_telehealth_2026-01-21.txt 221-274); "HG-A112 | VC-112A | January 21 13:00 | January 21 13:20" (BH-D106_telehealth_2026-01-21.txt 1462-1517)
- disputed: presence starts_at=2026-01-21T13:30, ends_at=2026-01-21T13:55 [final, authored 2026-01-21] "Patient contact occurred 13:00–13:20 and 13:30–13:55." (BH-D106_telehealth_2026-01-21.txt 221-274); "HG-A112 | VC-112B | January 21 13:30 | January 21 13:55" (BH-D106_telehealth_2026-01-21.txt 1518-1573)


## DEV-05

> Summarize the documented symptom course during the episode and the reason for the additional individual contact on January 19. Which symptom assessments are distinct, and what conclusions about progress can and cannot be supported?

| Instrument | Completed | Score | Status | Sources |
|---|---|---|---|---|
| PHQ-9 | 2026-01-05 | 18 | established (1 document(s)) | "PHQ-9 completed by Rowan on 2026-01-05: total score 18." (intake_and_individual_jan05.txt 1394-1449) |
| PHQ-9 | 2026-01-16 | 14 | established (2 document(s)) | "Instrument: PHQ-9 | Patient portal form HG-Q116" (symptom_measure_review_jan16.txt 191-238); "Completed by patient: 2026-01-16, 08:17 local" (symptom_measure_review_jan16.txt 239-284); "Total score: 14" (symptom_measure_review_jan16.txt 285-300)<br>"PHQ-9 | 14 | 2026-01-16 | HG-Q116" (imported_measure_summary_received_jan26.txt 572-615) |
| PHQ-9 | 2026-01-30 | 10 | established (1 document(s)) | "Questionnaire completed January 30, 2026, 12:42" (BH-D115_symptom_measure_review_2026-01-30.txt 137-184); "PHQ-9 total: 10. Item 9: 0." (BH-D115_symptom_measure_review_2026-01-30.txt 185-212) |

PHQ-9: 18 (2026-01-05) -> 14 (2026-01-16) -> 10 (2026-01-30); change first to last: -8.

**Documented observations:**
- 2026-01-05 HG-E101 [patient / symptom] Several weeks of low mood, reduced interest, fragmented sleep, and difficulty beginning tasks. "Rowan describes several weeks of low mood, reduced interest in usual activities, fragmented sleep, and difficulty beginning ordinary tasks." (intake_and_individual_jan05.txt 395-534)
- 2026-01-05 HG-E101 [patient / functioning] Postponing email replies, avoiding return-to-work conversations, and spending more time alone. "Rowan has been postponing email replies, avoiding conversations about the return date, and spending more time alone at home." (intake_and_individual_jan05.txt 611-735)
- 2026-01-05 HG-E101 [clinician / clinical_assessment] Depressive symptoms with anxiety and behavioral avoidance. "Clinical impressions are depressive symptoms with anxiety and behavioral avoidance." (intake_and_individual_jan05.txt 1503-1586)
- 2026-01-06 HG-E102 [patient / functioning] Delaying a reply to a work message for fear of being asked for a firm return date. "They described delaying a reply to a work message because they feared being asked for a firm return date." (group_facilitator_jan06.txt 1087-1192)
- 2026-01-08 HG-E103 [patient / functioning] Missed the morning appointment after a poor night of sleep. "They said the morning had gotten away from them after a poor night of sleep" (missed_visit_outreach_jan08.txt 840-915)
- 2026-01-09 HG-E104 [patient / functioning] Feels watched when repeatedly asked whether work has been contacted. "Rowan described feeling watched when asked repeatedly whether they had contacted work." (family_primary_jan09.txt 532-618)
- 2026-01-12 HG-E105 [patient / functioning] A weekend walk with Casey made the evening feel less dominated by worry. "They also described taking a walk with Casey over the weekend and noted that it helped the evening feel less dominated by worry." (group_facilitator_jan12.txt 1072-1200)
- 2026-01-13 HG-E106 [clinician / clinical_assessment] Ongoing depressive and anxiety symptoms with sleep disruption. "Assessment: ongoing depressive and anxiety symptoms with sleep disruption." (medication_review_jan13.txt 1175-1249)
- 2026-01-14 HG-E107 [patient / functioning] Opened a work message and took two short walks, but has not replied. "Rowan reported completing several small activities since the prior individual appointment, including opening a work message and taking two short walks." (individual_therapy_jan14.txt 357-508)
- 2026-01-14 HG-E107 [patient / symptom] Sleep remains interrupted and starting the morning requires effort. "Sleep remains interrupted, and getting started in the morning continues to require effort." (individual_therapy_jan14.txt 734-824)
- 2026-01-16 HG-E109 [collateral / functioning] Partner reports Rowan getting out for short walks and more willing to discuss the coming week. "Casey reported that Rowan had been getting out for short walks and seemed more willing to discuss the coming week." (partner_collateral_jan16.txt 683-797)
- 2026-01-16 HG-E109 [collateral / functioning] Partner reports difficult mornings and Rowan becoming quiet when work comes up. "Mornings remain difficult, and Casey described Rowan becoming quiet when the conversation turns to work." (partner_collateral_jan16.txt 798-902)
- 2026-01-16 [clinician / clinical_assessment] Score and session material suggest some improvement in depressive symptoms. "Clinician review: the score and recent individual-session material suggest some improvement in depressive symptoms." (symptom_measure_review_jan16.txt 717-832)
- 2026-01-16 [clinician / clinical_assessment] Persistent avoidance, difficulty initiating work communication, and sleep disruption remain relevant. "Persistent avoidance, difficulty initiating work communication, and sleep disruption remain clinically relevant." (symptom_measure_review_jan16.txt 833-945)
- 2026-01-19 HG-E110 [clinician / symptom] Became visibly tense when discussion turned to returning to the workplace; facilitator arranged a same-day individual meeting. "When discussion turned to returning to the workplace, Rowan became visibly tense and said the amount of discussion felt difficult to manage." (BH-D101_group_content_2026-01-19.txt 968-1108); "The facilitator offered grounding and arranged a same-day individual meeting with the treating clinician." (BH-D101_group_content_2026-01-19.txt 1109-1214)
- 2026-01-19 HG-E111 [clinician / visit_reason] Visit added because Rowan became anxious during group and needed individual grounding and coping review. "This visit was added because Rowan became anxious during group and needed individual grounding and review of coping strategies." (BH-D105_individual_2026-01-19.txt 254-381)
- 2026-01-19 HG-E111 [patient / symptom] Felt overwhelmed when group discussed workplace demands; worried about keeping up at work. "The patient described feeling overwhelmed when other members discussed workplace demands and worried that returning to work would expose difficulties keeping up." (BH-D105_individual_2026-01-19.txt 423-584)
- 2026-01-19 HG-E111 [patient / safety] Denied current suicidal thoughts; future oriented. "Rowan denied current suicidal thoughts and remained future oriented in discussing the next appointment." (BH-D105_individual_2026-01-19.txt 1180-1283)
- 2026-01-19 HG-E111 [clinician / functioning] Persistent avoidance and disrupted sleep interfere with resuming a work routine. "Persistent avoidance and disrupted sleep continue to interfere with resuming a usual work routine." (BH-D105_individual_2026-01-19.txt 1344-1442)
- 2026-01-21 HG-E112 [patient / functioning] Drafted a short message about a gradual return to work but stopped before sending. "Rowan reported drafting a short message about a possible gradual return to work but stopping before sending it." (BH-D106_telehealth_2026-01-21.txt 509-620)
- 2026-01-21 HG-E112 [patient / symptom] One night of improved sleep followed by a night of prolonged wakefulness. "Rowan described one night of improved sleep followed by a night of prolonged wakefulness." (BH-D106_telehealth_2026-01-21.txt 1011-1100)
- 2026-01-26 HG-E115 [patient / functioning] Sent a short message to the supervisor and received a request to discuss next steps. "Rowan described sending a short message to the supervisor and receiving a request to discuss possible next steps." (BH-D110_individual_primary_record_2026-01-26.txt 305-418)
- 2026-01-26 HG-E115 [clinician / functioning] Continued to postpone choosing a time for the conversation. "Rowan continued to postpone choosing a time for the conversation." (BH-D110_individual_primary_record_2026-01-26.txt 552-617)
- 2026-01-26 HG-E115 [patient / symptom] Sleep uneven, with difficulty settling when work thoughts become repetitive. "Sleep remained uneven, with difficulty settling on nights when work-related thoughts became repetitive." (BH-D110_individual_primary_record_2026-01-26.txt 618-721)
- 2026-01-26 HG-E115 [clinician / clinical_assessment] Presentation consistent with ongoing anxiety, low mood, and functional difficulty around work demands. "Clinical presentation remained consistent with ongoing anxiety, low mood, and functional difficulty around work demands." (BH-D111_individual_second_record_2026-01-26.txt 1348-1468)
- 2026-01-29 HG-E118 [patient / functioning] Opened the work calendar but delayed a follow-up conversation. "Rowan reported opening the work calendar but delaying a follow-up conversation." (BH-D107_group_activity_records_2026-01-22_and_29.txt 1222-1301)
- 2026-01-30 HG-E119 [clinician / functioning] Remained anxious about the work conversation but could explain the intended first step. "Rowan remained anxious about the work conversation but could explain the intended first step." (BH-D113_family_therapy_2026-01-30.txt 1238-1331)
- 2026-01-30 HG-E119 [patient / functioning] Having a limited plan felt more manageable. "The patient reported that having a limited plan felt more manageable." (BH-D113_family_therapy_2026-01-30.txt 1332-1401)
- 2026-01-30 HG-E120 [patient / symptom] Mood less persistently low than earlier in the month; anxiety noticeable when anticipating work contact; sleep variable. "Mood felt less persistently low than earlier in the month, although anxiety remained noticeable when anticipating contact with work." (BH-D114_medication_management_2026-01-30.txt 420-552); "Sleep was still variable." (BH-D114_medication_management_2026-01-30.txt 553-578)
- 2026-01-30 [clinician / clinical_assessment] Partial improvement, with persistent avoidance and meaningful functional impact around returning to work. "Clinician review, January 30: Rowan shows partial improvement, with persistent avoidance and meaningful functional impact around returning to work." (BH-D115_symptom_measure_review_2026-01-30.txt 540-687)
- 2026-01-30 [clinician / symptom] Sleep disruption remains an intermittent barrier to a steadier routine. "Sleep disruption remains an intermittent barrier to establishing a steadier daytime routine." (BH-D115_symptom_measure_review_2026-01-30.txt 879-971)

**Limits:**
- Assessments with the same source form identifier and completion date are one assessment; imported copies are additional sources. Distinct form identifiers are distinct assessments. Results without a form identifier are not merged across documents.
- Scores and observations are reported as documented and attributed to their reporter; remission, recovery, work readiness, and treatment causation are not inferred.
