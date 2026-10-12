# Answers

Generated from reconciliation run 2 (extraction version `llm-v2`, 31 documents reconciled, 0 not extracted). Full structured results: `answers.json`.

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

**Goal** (2026-01-05 to 2026-01-30): at least 3 therapy days and 150 minutes per Monday-Sunday week; counted services: family_therapy, group_therapy, individual_therapy. Source: "Episode dates: 2026-01-05 through 2026-01-30"; "Local treatment participation goal: at least 3 therapy days and at least 150 minutes of patient-present therapy in each Monday–Sunday week."; "A therapy day is a calendar day on which Rowan participates in individual, group, or family psychotherapy."; "Patient-present individual, group, and family therapy contribute to the minute goal."

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
- accepted: attendance attendance=attended [final, authored 2026-01-19] "Patient arrival: 10:00 | Patient departure: 11:30 | Status: Attended" (BH-D102_original_attendance_2026-01-19.txt 296-364)
- accepted: attendance attendance=attended [final, authored 2026-01-19] "Rowan initially followed the exercise and identified postponing a message to a supervisor as a familiar pattern." (BH-D101_group_content_2026-01-19.txt 855-967); "When discussion turned to returning to the workplace, Rowan became visibly tense and said the amount of discussion felt difficult to manage." (BH-D101_group_content_2026-01-19.txt 968-1108)
- accepted: attendance attendance=attended [final, authored 2026-01-19] "Patient arrival: 10:00 | Patient departure: 11:30 | Status: Attended" (BH-D104_resent_roster_received_2026-01-26.txt 789-857)
- accepted: break starts_at=2026-01-19T10:45, ends_at=2026-01-19T11:00 [final, authored 2026-01-19] "Scheduled group: 10:00–11:30. Nontherapeutic break: 10:45–11:00." (BH-D101_group_content_2026-01-19.txt 231-295)
- applied_correction (applied through a matching dated correction chain): correction corrected_field=presence_end, replaced_value=2026-01-19T11:30, replacement_value=2026-01-19T11:15 [final, authored 2026-01-20] "Applies to group encounter HG-E110, service date January 19, 2026" (BH-D103_attendance_correction_2026-01-20.txt 156-221); "Correction: Patient departure for HG-E110 is 11:15, replacing the original roster value of 11:30. Patient arrival remains 10:00." (BH-D103_attendance_correction_2026-01-20.txt 223-351); "Electronically signed: Leah Chen, LCSW | January 20, 2026, 08:42" (BH-D103_attendance_correction_2026-01-20.txt 1355-1419)
- accepted: encounter_detail service_date=2026-01-19, service_type=group_therapy [final, authored 2026-01-19] "Service date: January 19, 2026 | Group encounter: HG-E110" (BH-D102_original_attendance_2026-01-19.txt 95-152); "Patient: Rowan Mercer | DOB: 1991-04-12 | MRN: HG-M042" (BH-D102_original_attendance_2026-01-19.txt 153-207); "This is the patient row from the facilitator's attendance sheet." (BH-D102_original_attendance_2026-01-19.txt 400-464)
- accepted: encounter_detail service_date=2026-01-19, service_type=group_therapy [final, authored 2026-01-19] "Skills group clinical record | Service date: January 19, 2026" (BH-D101_group_content_2026-01-19.txt 52-113); "Group encounter: HG-E110 | Facilitator: Leah Chen, LCSW" (BH-D101_group_content_2026-01-19.txt 114-169); "Scheduled group: 10:00–11:30. Nontherapeutic break: 10:45–11:00." (BH-D101_group_content_2026-01-19.txt 231-295)
- accepted: encounter_detail service_date=2026-01-19, service_type=group_therapy [final, authored 2026-01-19] "Service date: January 19, 2026 | Group encounter: HG-E110" (BH-D104_resent_roster_received_2026-01-26.txt 644-701); "Patient arrival: 10:00 | Patient departure: 11:30 | Status: Attended" (BH-D104_resent_roster_received_2026-01-26.txt 789-857); "Original signature: Leah Chen, LCSW | January 19, 2026, 12:14" (BH-D104_resent_roster_received_2026-01-26.txt 858-919); "Original disposition: Final, signed" (BH-D104_resent_roster_received_2026-01-26.txt 920-955)
- corrected (presence_end 11:30 -> 11:15): presence starts_at=2026-01-19T10:00, ends_at=2026-01-19T11:30 [final, authored 2026-01-19] "Patient arrival: 10:00 | Patient departure: 11:30 | Status: Attended" (BH-D102_original_attendance_2026-01-19.txt 296-364)
- corrected (presence_end 11:30 -> 11:15): presence starts_at=2026-01-19T10:00, ends_at=2026-01-19T11:30 [final, authored 2026-01-19] "Patient arrival: 10:00 | Patient departure: 11:30 | Status: Attended" (BH-D104_resent_roster_received_2026-01-26.txt 789-857)

**HG-E111** (individual_therapy, included: patient attended eligible therapy); duration established: 11:15-11:45 (30) = 30 min
- accepted: attendance attendance=attended [final, authored 2026-01-19] "Patient contact: 11:15–11:45 | Completed: 30 minutes" (BH-D105_individual_2026-01-19.txt 172-224)
- accepted: encounter_detail service_date=2026-01-19, service_type=individual_therapy [final, authored 2026-01-19] "Individual psychotherapy | Encounter HG-E111" (BH-D105_individual_2026-01-19.txt 52-96)
- accepted: presence starts_at=2026-01-19T11:15, ends_at=2026-01-19T11:45 [final, authored 2026-01-19] "Patient contact: 11:15–11:45 | Completed: 30 minutes" (BH-D105_individual_2026-01-19.txt 172-224)

### 2026-01-21: 1 therapy contact(s), 45 minutes

**HG-E112** (individual_therapy, included: patient attended eligible therapy); duration established: 13:00-13:20 (20) + 13:30-13:55 (25) = 45 min
- accepted: attendance attendance=attended [final, authored 2026-01-21] "Patient contact occurred 13:00–13:20 and 13:30–13:55." (BH-D106_telehealth_2026-01-21.txt 221-274)
- accepted: break starts_at=2026-01-21T13:20, ends_at=2026-01-21T13:30 [final, authored 2026-01-21] "Connection was lost from 13:20–13:30; there was no therapeutic contact during that interval." (BH-D106_telehealth_2026-01-21.txt 275-367)
- accepted: encounter_detail service_date=2026-01-21, service_type=individual_therapy [final, authored 2026-01-21] "Individual psychotherapy | Encounter HG-E112 | Appointment HG-A112" (BH-D106_telehealth_2026-01-21.txt 52-118); "January 21, 2026 | Video | Clinician: Mira Patel, LCSW" (BH-D106_telehealth_2026-01-21.txt 165-219)
- accepted: presence starts_at=2026-01-21T13:00, ends_at=2026-01-21T13:20 [final, authored 2026-01-21] "Patient contact occurred 13:00–13:20" (BH-D106_telehealth_2026-01-21.txt 221-257)
- accepted: presence starts_at=2026-01-21T13:30, ends_at=2026-01-21T13:55 [final, authored 2026-01-21] "and 13:30–13:55." (BH-D106_telehealth_2026-01-21.txt 258-274)


## DEV-05

> Summarize the documented symptom course during the episode and the reason for the additional individual contact on January 19. Which symptom assessments are distinct, and what conclusions about progress can and cannot be supported?

| Instrument | Completed | Score | Status | Sources |
|---|---|---|---|---|
| PHQ-9 | 2026-01-05 | 18 | established (1 document(s)) | "PHQ-9 completed by Rowan on 2026-01-05: total score 18." (intake_and_individual_jan05.txt 1394-1449) |
| PHQ-9 | 2026-01-16 | 14 | established (2 document(s)) | "Measure | Result | Date completed | Source form PHQ-9 | 14 | 2026-01-16 | HG-Q116" (imported_measure_summary_received_jan26.txt 524-615); "The source form identifier and original completion date were retained in the imported row." (imported_measure_summary_received_jan26.txt 1120-1210)<br>"Instrument: PHQ-9 | Patient portal form HG-Q116" (symptom_measure_review_jan16.txt 191-238); "Completed by patient: 2026-01-16, 08:17 local" (symptom_measure_review_jan16.txt 239-284); "Total score: 14" (symptom_measure_review_jan16.txt 285-300) |
| PHQ-9 | 2026-01-30 | 10 | established (1 document(s)) | "Questionnaire completed January 30, 2026, 12:42 PHQ-9 total: 10. Item 9: 0." (BH-D115_symptom_measure_review_2026-01-30.txt 137-212) |

PHQ-9: 18 (2026-01-05) -> 14 (2026-01-16) -> 10 (2026-01-30); change first to last: -8.

**Documented observations:**
- 2026-01-05 HG-E101 [patient / visit_reason] Several weeks of low mood, reduced interest in usual activities, fragmented sleep, and difficulty starting ordinary tasks. "Reason for care: Rowan describes several weeks of low mood, reduced interest in usual activities, fragmented sleep, and difficulty beginning ordinary tasks." (intake_and_individual_jan05.txt 378-534)
- 2026-01-05 HG-E101 [patient / functioning] Returning to work after recent leave increases worry. "Worry increases when thinking about returning to work after a recent leave." (intake_and_individual_jan05.txt 535-610)
- 2026-01-05 HG-E101 [patient / functioning] They have been postponing email replies, avoiding conversations about the return date, and spending more time alone at home. "Rowan has been postponing email replies, avoiding conversations about the return date, and spending more time alone at home." (intake_and_individual_jan05.txt 611-735)
- 2026-01-05 HG-E101 [clinician / clinical_assessment] Speech was clear and organized; affect was subdued but responsive, especially when discussing partner support. "Speech was clear and organized. Affect was subdued but responsive, especially when discussing their partner's support." (intake_and_individual_jan05.txt 991-1109)
- 2026-01-05 HG-E101 [clinician / safety] No immediate safety concern was identified; they could discuss support contacts and ways to seek additional help if needed. "No immediate safety concern was identified in today's assessment; Rowan was able to discuss support contacts and ways to seek additional help if needed." (intake_and_individual_jan05.txt 1240-1392)
- 2026-01-05 [clinician / visit_reason] Depressed mood, sleep disruption, anxiety about resuming work responsibilities, and avoidance of tasks and communication. "Presenting needs: depressed mood, sleep disruption, anxiety about resuming work responsibilities, and avoidance of tasks and communication." (signed_treatment_plan_jan05.txt 355-494)
- 2026-01-05 [clinician / functioning] Partner support is available, though repeated reminders sometimes increase tension. "Partner support is available but repeated reminders sometimes increase tension." (signed_treatment_plan_jan05.txt 576-655)
- 2026-01-06 HG-E102 [patient / functioning] Delayed replying to a work message due to fear of being asked for a firm return date. "They described delaying a reply to a work message because they feared being asked for a firm return date." (group_facilitator_jan06.txt 1087-1192)
- 2026-01-06 HG-E102 [clinician / clinical_assessment] Participation was relevant to the topic and they appeared receptive to peer suggestions. "Their participation was relevant to the topic, and they appeared receptive to peer suggestions." (group_facilitator_jan06.txt 1319-1414)
- 2026-01-08 HG-E103 [patient / symptom] Rowan reported a poor night's sleep and said the morning got away from them. "They said the morning had gotten away from them after a poor night of sleep and confirmed that they still intended to attend the next day's visit with Casey." (missed_visit_outreach_jan08.txt 840-997)
- 2026-01-09 HG-E104 [clinician / visit_reason] Visit focused on patterns of support at home while Rowan tried to rebuild a routine. "The appointment focused on patterns of support at home as Rowan attempts to rebuild a routine." (family_primary_jan09.txt 437-531)
- 2026-01-09 HG-E104 [patient / symptom] Rowan felt watched when repeatedly asked whether they had contacted work. "Rowan described feeling watched when asked repeatedly whether they had contacted work." (family_primary_jan09.txt 532-618)
- 2026-01-09 HG-E104 [collateral / functioning] Casey worried that giving Rowan space might leave them isolated. "Casey described worry that giving Rowan space might leave them isolated." (family_primary_jan09.txt 619-691)
- 2026-01-09 HG-E104 [clinician / functioning] Rowan remained present and engaged throughout the visit. "Rowan remained present and engaged throughout the visit." (family_primary_jan09.txt 1171-1227)
- 2026-01-09 HG-E104 [clinician / functioning] Rowan became more animated when describing a shared evening walk and identified it as support that did not feel like pressure. "They became more animated when describing a shared evening walk and identified this as support that did not feel like pressure." (family_primary_jan09.txt 1228-1355)
- 2026-01-09 HG-E104 [clinician / clinical_assessment] Both acknowledged that their intentions differed from how the other person experienced the exchange. "Both were able to acknowledge that their intentions differed from how the other person experienced the exchange." (family_primary_jan09.txt 692-804)
- 2026-01-10 HG-E104 [clinician / visit_reason] Family appointment focused on communication practice and observing reactions to slowing an anxious exchange. "Accompanying clinical entry for the family appointment facilitated with Mara Voss. My role was to assist with communication practice and observe how the couple responded when slowing down an anxious exchange." (family_cofacilitator_jan09.txt 417-625)
- 2026-01-10 HG-E104 [patient / functioning] Rowan felt partner reminders meant they were falling behind. "Rowan initially described partner reminders as evidence that they were falling behind." (family_cofacilitator_jan09.txt 626-712)
- 2026-01-10 HG-E104 [collateral / functioning] Casey saw the reminders as intended to help, but said repeated prompts increased tension. "Casey explained that the reminders were an attempt to help, while also recognizing that repeated prompts increased tension." (family_cofacilitator_jan09.txt 713-836) Attribution reviewed from patient to collateral; the original assertion is unchanged.
- 2026-01-10 HG-E104 [clinician / clinical_assessment] The rehearsal became less defensive with repetition. "The rehearsal became less defensive with repetition." (family_cofacilitator_jan09.txt 1099-1151)
- 2026-01-10 HG-E104 [clinician / functioning] The couple generated ideas for a brief, predictable check-in. "Both participants contributed ideas for a brief, predictable check-in." (family_cofacilitator_jan09.txt 1152-1222)
- 2026-01-10 HG-E104 [clinician / functioning] The couple chose an evening walk as shared time that would not turn into a discussion of progress. "The couple selected an evening walk as an activity they could share without making it a discussion about progress." (family_cofacilitator_jan09.txt 1224-1338)
- 2026-01-10 HG-E104 [patient / functioning] Rowan said the evening walk felt more acceptable than a lengthy review of unfinished tasks. "Rowan said this felt more acceptable than a lengthy review of unfinished tasks." (family_cofacilitator_jan09.txt 1339-1418)
- 2026-01-12 HG-E105 [patient / functioning] The patient described leaving work messages unopened as a coping example. "Rowan contributed an example about leaving work messages unopened." (group_facilitator_jan12.txt 906-972)
- 2026-01-12 HG-E105 [patient / functioning] The patient framed checking one message as a smaller step than answering all outstanding messages. "They identified looking at one message as a lower step than replying to every outstanding message." (group_facilitator_jan12.txt 973-1071)
- 2026-01-12 HG-E105 [patient / symptom] The patient said a weekend walk with Casey made the evening feel less dominated by worry. "They also described taking a walk with Casey over the weekend and noted that it helped the evening feel less dominated by worry." (group_facilitator_jan12.txt 1072-1200)
- 2026-01-12 HG-E105 [patient / functioning] The patient planned an action to try after breakfast and asked how to handle a bad morning. "During the planning exercise, Rowan wrote down an action to try after breakfast and asked how to respond if the morning went poorly." (group_facilitator_jan12.txt 1201-1333)
- 2026-01-12 HG-E105 [clinician / functioning] The patient listened to peers and gave another member a supportive comment. "Rowan listened to peers and offered a supportive comment to another member." (group_facilitator_jan12.txt 1424-1499)
- 2026-01-13 HG-E106 [patient / symptom] Patient reported ongoing sleep interruption and daytime tiredness. "Rowan reported continuing sleep interruption and daytime tiredness." (medication_review_jan13.txt 507-574)
- 2026-01-13 HG-E106 [patient / symptom] Patient said mood felt somewhat less heavy on days with a planned activity and that they remained concerned about work communication. "They described mood as somewhat less heavy on days with a planned activity but remained concerned about work communication." (medication_review_jan13.txt 575-698)
- 2026-01-13 HG-E106 [patient / safety] Patient denied a new medication-related concern requiring urgent intervention. "Rowan denied a new medication-related concern requiring urgent intervention." (medication_review_jan13.txt 782-858)
- 2026-01-13 HG-E106 [clinician / functioning] Patient was attentive, asked questions about the monitoring plan, and could restate the next steps. "Rowan was attentive, asked questions about the monitoring plan, and could restate the next steps." (medication_review_jan13.txt 1020-1117)
- 2026-01-13 HG-E106 [clinician / clinical_assessment] No new physical complaint was raised during this visit. "No new physical complaint was raised during this visit." (medication_review_jan13.txt 1118-1173)
- 2026-01-13 HG-E106 [clinician / clinical_assessment] Ongoing depressive and anxiety symptoms with sleep disruption. "Assessment: ongoing depressive and anxiety symptoms with sleep disruption." (medication_review_jan13.txt 1175-1249)
- 2026-01-13 HG-E106 [clinician / functioning] Patient is engaged with the therapy program and intends to continue scheduled appointments. "Rowan is engaged with the therapy program and intends to continue the scheduled appointments." (medication_review_jan13.txt 1250-1343)
- 2026-01-14 HG-E107 [patient / functioning] Patient completed several small activities, including opening a work message and taking two short walks. "Rowan reported completing several small activities since the prior individual appointment, including opening a work message and taking two short walks." (individual_therapy_jan14.txt 357-508)
- 2026-01-14 HG-E107 [patient / symptom] Patient has not replied to the work message and continues to expect questions they cannot answer. "They have not yet replied to the message and continue to imagine being asked questions they cannot answer." (individual_therapy_jan14.txt 509-615)
- 2026-01-14 HG-E107 [patient / functioning] The family appointment felt helpful because the planned check-in with Casey reduced repeated reminders. "Rowan described the family appointment as helpful because the planned check-in with Casey reduced repeated reminders." (individual_therapy_jan14.txt 616-733)
- 2026-01-14 HG-E107 [patient / symptom] Sleep remains interrupted and mornings still take effort to get started. "Sleep remains interrupted, and getting started in the morning continues to require effort." (individual_therapy_jan14.txt 734-824)
- 2026-01-14 HG-E107 [patient / symptom] Patient noticed physical tension during the rehearsal but stayed with the task. "Rowan noticed physical tension during the rehearsal but was able to remain with the task." (individual_therapy_jan14.txt 1067-1156)
- 2026-01-14 HG-E107 [patient / functioning] The drafted message felt less overwhelming when framed as a brief acknowledgment rather than a full return-to-work solution. "They said the message seemed less overwhelming when it did not need to solve the entire return-to-work question." (individual_therapy_jan14.txt 1157-1269)
- 2026-01-14 HG-E107 [clinician / clinical_assessment] Affect was more varied than at intake, with worry evident when discussing employment. "Affect was more varied than at intake, although worry was evident when discussing employment." (individual_therapy_jan14.txt 1519-1612)
- 2026-01-16 [clinician / clinical_assessment] Some improvement in depressive symptoms, with ongoing avoidance of work communication and inconsistent sleep; continue current therapeutic focus and review practical functioning at the next direct appointment. "Source review excerpt, Mara Voss, LCSW: some improvement in depressive symptoms; ongoing avoidance of work communication and inconsistent sleep." (imported_measure_summary_received_jan26.txt 617-761); "Continue current therapeutic focus and review practical functioning at the next direct appointment." (imported_measure_summary_received_jan26.txt 762-861)
- 2026-01-16 [patient / functioning] Getting out of the apartment has become a little easier, but thinking about work still leads to procrastination. "In the optional update field, Rowan wrote that getting out of the apartment had become a little easier, while thinking about work continued to make them want to put things off." (symptom_measure_review_jan16.txt 435-611)
- 2026-01-16 [patient / symptom] Sleep is inconsistent. "Rowan also described sleep as inconsistent." (symptom_measure_review_jan16.txt 612-655)
- 2026-01-16 [clinician / clinical_assessment] There appears to be some improvement in depressive symptoms. "Clinician review: the score and recent individual-session material suggest some improvement in depressive symptoms." (symptom_measure_review_jan16.txt 717-832)
- 2026-01-16 [clinician / clinical_assessment] Persistent avoidance, difficulty initiating work communication, and sleep disruption remain clinically relevant. "Persistent avoidance, difficulty initiating work communication, and sleep disruption remain clinically relevant." (symptom_measure_review_jan16.txt 833-945)
- 2026-01-16 [clinician / functioning] They have tried small activities and communication practice but have not yet established a reliable routine. "Rowan has attempted small activities and communication practice but has not yet established a reliable routine." (symptom_measure_review_jan16.txt 946-1057)
- 2026-01-16 HG-E109 [collateral / visit_reason] Collateral discussion focused on home observations and support for the treatment plan. "This was a collateral discussion with Casey only, focused on observations at home and ways to support the treatment plan." (partner_collateral_jan16.txt 560-681)
- 2026-01-16 HG-E109 [collateral / functioning] Rowan had been getting out for short walks and seemed more willing to discuss the coming week. "Casey reported that Rowan had been getting out for short walks and seemed more willing to discuss the coming week." (partner_collateral_jan16.txt 683-797)
- 2026-01-16 HG-E109 [collateral / functioning] Mornings remain difficult and Rowan becomes quiet when the conversation turns to work. "Mornings remain difficult, and Casey described Rowan becoming quiet when the conversation turns to work." (partner_collateral_jan16.txt 798-902)
- 2026-01-16 HG-E109 [collateral / functioning] The scheduled evening check-in has reduced unplanned reminders. "The scheduled evening check-in has reduced unplanned reminders." (partner_collateral_jan16.txt 903-966)
- 2026-01-16 HG-E109 [collateral / functioning] Casey has noticed less argument when asking what kind of help Rowan wants. "it takes effort to resist offering multiple solutions but has noticed less argument when asking what kind of help Rowan wants." (partner_collateral_jan16.txt 978-1104)
- 2026-01-19 HG-E110 [patient / symptom] The patient identified anxiety about reconnecting with work. "Rowan was present for the opening check-in." (BH-D102_original_attendance_2026-01-19.txt 723-766); "The patient identified anxiety about reconnecting with work and accepted an exercise handout." (BH-D102_original_attendance_2026-01-19.txt 767-860); "Staff arranged access to the individual clinician after Rowan requested additional help." (BH-D102_original_attendance_2026-01-19.txt 861-949)
- 2026-01-19 HG-E110 [patient / functioning] Rowan requested additional help and staff arranged access to the individual clinician. "Staff arranged access to the individual clinician after Rowan requested additional help." (BH-D102_original_attendance_2026-01-19.txt 861-949)
- 2026-01-19 HG-E110 [clinician / clinical_assessment] Rowan recognized a familiar avoidant pattern during the exercise. "The facilitator used a worked example involving an unanswered work email." (BH-D101_group_content_2026-01-19.txt 449-522); "Rowan initially followed the exercise and identified postponing a message to a supervisor as a familiar pattern." (BH-D101_group_content_2026-01-19.txt 855-967)
- 2026-01-19 HG-E110 [patient / symptom] Rowan said the amount of discussion felt difficult to manage and appeared tense when workplace return was discussed. "When discussion turned to returning to the workplace, Rowan became visibly tense and said the amount of discussion felt difficult to manage." (BH-D101_group_content_2026-01-19.txt 968-1108)
- 2026-01-19 HG-E110 [clinician / visit_reason] requested additional help from the individual clinician "Attachment remarks retained from original: Rowan attended the opening check-in, accepted the exercise handout, and requested additional help from the individual clinician. Group content is recorded separately." (BH-D104_resent_roster_received_2026-01-26.txt 957-1166)
- 2026-01-19 HG-E111 [clinician / visit_reason] The visit was added because Rowan became anxious during group and needed grounding and coping review. "This visit was added because Rowan became anxious during group and needed individual grounding and review of coping strategies." (BH-D105_individual_2026-01-19.txt 254-381)
- 2026-01-19 HG-E111 [patient / symptom] Rowan felt overwhelmed by discussion of workplace demands and worried about managing work. "The patient described feeling overwhelmed when other members discussed workplace demands and worried that returning to work would expose difficulties keeping up." (BH-D105_individual_2026-01-19.txt 423-584)
- 2026-01-19 HG-E111 [clinician / symptom] Rowan identified muscle tension, rapid breathing, and an urge to leave as early signs of activation. "Rowan was able to identify muscle tension, rapid breathing, and an urge to leave as early signs of activation." (BH-D105_individual_2026-01-19.txt 585-695)
- 2026-01-19 HG-E111 [clinician / safety] Rowan denied current suicidal thoughts and no acute safety concern was identified. "Rowan denied current suicidal thoughts and remained future oriented in discussing the next appointment." (BH-D105_individual_2026-01-19.txt 1180-1283); "No acute safety concern was identified during this contact." (BH-D105_individual_2026-01-19.txt 1284-1343)
- 2026-01-19 HG-E111 [clinician / functioning] Avoidance and disrupted sleep are interfering with returning to a usual work routine. "Persistent avoidance and disrupted sleep continue to interfere with resuming a usual work routine." (BH-D105_individual_2026-01-19.txt 1344-1442)
- 2026-01-21 HG-E112 [patient / functioning] The patient was drafting a message about a gradual return to work but did not send it. "Rowan reported drafting a short message about a possible gradual return to work but stopping before sending it." (BH-D106_telehealth_2026-01-21.txt 509-620)
- 2026-01-21 HG-E112 [patient / functioning] Repeatedly checking the draft was delaying the task. "The patient identified checking the draft repeatedly as another way the task was being delayed." (BH-D106_telehealth_2026-01-21.txt 745-840)
- 2026-01-21 HG-E112 [clinician / clinical_assessment] The session practiced reading the draft once and selecting a planned time to send it. "Practiced reading the draft once and choosing a planned time to send it." (BH-D106_telehealth_2026-01-21.txt 841-913)
- 2026-01-21 HG-E112 [patient / symptom] The patient described one night of improved sleep followed by a night of prolonged wakefulness. "Rowan described one night of improved sleep followed by a night of prolonged wakefulness." (BH-D106_telehealth_2026-01-21.txt 1011-1100)
- 2026-01-21 HG-E112 [clinician / functioning] The patient was engaged and able to restate the agreed task. "Rowan was engaged and able to restate the agreed task." (BH-D106_telehealth_2026-01-21.txt 1163-1217)
- 2026-01-21 HG-E112 [clinician / safety] No urgent safety concern was reported. "No urgent safety concern was reported." (BH-D106_telehealth_2026-01-21.txt 1218-1256)
- 2026-01-21 HG-E112 [clinician / clinical_assessment] Follow-up remains with the established outpatient team. "Follow-up remains with the established outpatient team." (BH-D106_telehealth_2026-01-21.txt 1257-1312)
- 2026-01-22 HG-E113 [patient / functioning] Patient said seeing outstanding items on the work calendar would feel overwhelming. "Rowan used opening a work calendar as an example and described concern that seeing outstanding items would become overwhelming." (BH-D107_group_activity_records_2026-01-22_and_29.txt 614-741)
- 2026-01-23 HG-E114 [collateral / visit_reason] Coordination focused on practical supports related to returning to work. "With the patient's existing release on file, discussed coordination of practical supports related to returning to work." (BH-D109_care_coordination_2026-01-23.txt 297-416)
- 2026-01-23 HG-E114 [collateral / functioning] Rowan asked for help understanding whom to contact about a gradual return schedule. "The outside social worker reported that Rowan had asked for help understanding whom to contact about a gradual return schedule." (BH-D109_care_coordination_2026-01-23.txt 417-544)
- 2026-01-26 HG-E115 [patient / visit_reason] Patient described messaging the supervisor and being asked to discuss possible next steps. "Rowan described sending a short message to the supervisor and receiving a request to discuss possible next steps." (BH-D110_individual_primary_record_2026-01-26.txt 305-418)
- 2026-01-26 HG-E115 [patient / symptom] Sleep was uneven, with difficulty settling when work-related thoughts kept repeating at night. "Sleep remained uneven, with difficulty settling on nights when work-related thoughts became repetitive." (BH-D110_individual_primary_record_2026-01-26.txt 618-721)
- 2026-01-26 HG-E115 [clinician / functioning] Patient was attentive and collaborative but hesitant to complete the task outside the office. "The patient remained attentive and collaborative, although hesitant about completing the task outside the office." (BH-D110_individual_primary_record_2026-01-26.txt 1154-1267)
- 2026-01-26 HG-E115 [clinician / safety] No current suicidal ideation was reported. "No current suicidal ideation was reported." (BH-D110_individual_primary_record_2026-01-26.txt 1268-1310)
- 2026-01-26 HG-E115 [patient / functioning] Difficulty moving from a supervisor's reply to arranging the next conversation. "Rowan discussed difficulty moving from a supervisor's reply to arranging the next conversation." (BH-D111_individual_second_record_2026-01-26.txt 582-677)
- 2026-01-26 HG-E115 [patient / symptom] Anticipated becoming overwhelmed if several work issues were raised at once. "The patient anticipated becoming overwhelmed if several work issues were raised at once." (BH-D111_individual_second_record_2026-01-26.txt 678-766)
- 2026-01-26 HG-E115 [patient / functioning] Tends to keep editing a message after the essential point is already clear. "Rowan recognized a tendency to keep editing a message after the essential point was already clear." (BH-D111_individual_second_record_2026-01-26.txt 899-997)
- 2026-01-26 HG-E115 [patient / functioning] Could use the cue during rehearsal but remained uncertain about using it independently when anxious. "The patient could use the cue during the rehearsal but remained uncertain about using it independently when anxious." (BH-D111_individual_second_record_2026-01-26.txt 1138-1254)
- 2026-01-26 HG-E115 [clinician / symptom] Repetitive planning at night affected settling for sleep. "The discussion also addressed how repetitive planning at night affected settling for sleep." (BH-D111_individual_second_record_2026-01-26.txt 1255-1346)
- 2026-01-26 HG-E115 [clinician / clinical_assessment] Ongoing anxiety, low mood, and functional difficulty around work demands. "Clinical presentation remained consistent with ongoing anxiety, low mood, and functional difficulty around work demands." (BH-D111_individual_second_record_2026-01-26.txt 1348-1468)
- 2026-01-26 HG-E115 [patient / functioning] Was engaged with the treatment team and wished to resume a steadier routine. "Rowan was engaged with the treatment team and described a wish to resume a steadier routine." (BH-D111_individual_second_record_2026-01-26.txt 1469-1561)
- 2026-01-29 HG-E118 [patient / functioning] Patient opened the work calendar but delayed a follow-up conversation. "Rowan reported opening the work calendar but delaying a follow-up conversation." (BH-D107_group_activity_records_2026-01-22_and_29.txt 1222-1301)
- 2026-01-29 HG-E118 [patient / functioning] Patient participated in paired rehearsal and accepted feedback to keep the request brief. "Rowan participated in the paired rehearsal and accepted feedback about keeping the request brief." (BH-D107_group_activity_records_2026-01-22_and_29.txt 1418-1515)
- 2026-01-30 [patient / functioning] The patient completed the questionnaire before the afternoon appointment. "Rowan completed the questionnaire before the afternoon appointment." (BH-D115_symptom_measure_review_2026-01-30.txt 214-281)
- 2026-01-30 [patient / symptom] The patient continued to report sleep difficulty, trouble sustaining usual activities, and fewer days of pervasive low mood than at intake. "The patient continued to endorse sleep difficulty and trouble sustaining usual activities, with fewer days of pervasive low mood than reported at intake." (BH-D115_symptom_measure_review_2026-01-30.txt 282-435)
- 2026-01-30 [clinician / clinical_assessment] The clinician noted partial improvement with persistent avoidance and meaningful functional impact around returning to work. "Clinician review, January 30: Rowan shows partial improvement, with persistent avoidance and meaningful functional impact around returning to work." (BH-D115_symptom_measure_review_2026-01-30.txt 540-687)
- 2026-01-30 [clinician / functioning] The patient has taken initial steps but still delays follow-up and becomes anxious when tasks expand beyond a narrowly defined action. "The patient has taken some initial steps, including drafting and sending a message, but continues to delay follow-up and becomes anxious when a task expands beyond a narrowly defined action." (BH-D115_symptom_measure_review_2026-01-30.txt 688-878)
- 2026-01-30 [clinician / symptom] Sleep disruption remains an intermittent barrier to a steadier daytime routine. "Sleep disruption remains an intermittent barrier to establishing a steadier daytime routine." (BH-D115_symptom_measure_review_2026-01-30.txt 879-971)
- 2026-01-30 [clinician / functioning] Family support may help the patient carry out agreed tasks between appointments. "Family support may help the patient carry out the agreed tasks between appointments." (BH-D115_symptom_measure_review_2026-01-30.txt 1309-1393)
- 2026-01-30 HG-E120 [patient / symptom] Reported taking the medication as prescribed and no new adverse effect. "Rowan reported taking the medication as prescribed and did not describe a new adverse effect." (BH-D114_medication_management_2026-01-30.txt 326-419)
- 2026-01-30 HG-E120 [patient / symptom] Mood was less persistently low than earlier in the month, but anxiety remained noticeable when anticipating contact with work. "Mood felt less persistently low than earlier in the month, although anxiety remained noticeable when anticipating contact with work." (BH-D114_medication_management_2026-01-30.txt 420-552)
- 2026-01-30 HG-E120 [patient / symptom] Sleep remained variable. "Sleep was still variable." (BH-D114_medication_management_2026-01-30.txt 553-578)
- 2026-01-30 HG-E120 [clinician / clinical_assessment] Alert, organized in conversation, and able to describe the follow-up plan. "Rowan was alert, organized in conversation, and able to describe the follow-up plan." (BH-D114_medication_management_2026-01-30.txt 670-754)
- 2026-01-30 HG-E120 [patient / safety] Denied current suicidal thoughts. "The patient denied current suicidal thoughts." (BH-D114_medication_management_2026-01-30.txt 755-800)
- 2026-01-30 HG-E120 [clinician / safety] No new acute safety issue emerged in this visit. "No new acute safety issue emerged in this visit." (BH-D114_medication_management_2026-01-30.txt 801-849)
- 2026-01-30 HG-E120 [clinician / visit_reason] Medication evaluation and management with symptom review and medication counseling. "The service consisted of medication evaluation and management, including symptom review and medication counseling." (BH-D114_medication_management_2026-01-30.txt 1074-1188)
- 2026-01-30 HG-E119 [collateral / functioning] Casey was unsure when reminders helped versus increased pressure for Rowan. "Casey described uncertainty about when reminders helped and when they seemed to increase Rowan's sense of pressure." (BH-D113_family_therapy_2026-01-30.txt 407-522)
- 2026-01-30 HG-E119 [clinician / symptom] Rowan remained anxious about the work conversation but could explain the intended first step. "Rowan remained anxious about the work conversation but could explain the intended first step." (BH-D113_family_therapy_2026-01-30.txt 1238-1331)
- 2026-01-30 HG-E119 [patient / functioning] The patient said a limited plan felt more manageable. "The patient reported that having a limited plan felt more manageable." (BH-D113_family_therapy_2026-01-30.txt 1332-1401)

**Limits:**
- Assessments with the same source form identifier and completion date are one assessment; imported copies are additional sources. Distinct form identifiers are distinct assessments. Results without a form identifier are not merged across documents.
- Scores and observations are reported as documented and attributed to their reporter; remission, recovery, work readiness, and treatment causation are not inferred.
