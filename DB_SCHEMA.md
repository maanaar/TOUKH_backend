# SayCare  - Database Schema Reference

## New models (own tables)

### Hospital structure

- hospital.accommodation.grade.type -> hospital_accommodation_grade_type
  name (Char, uniq), sequence, active

- hospital.accommodation.grade -> hospital_accommodation_grade
  code (uniq), name (M2one to hospital.accommodation.grade.type, required), price_per_day,
  include_nursing, include_meals, need_approval

- hospital.floor -> hospital_floor
  code, name, building, floor_no
  M2M to hospital.inpatient.department via hospital_floor_department_rel

- hospital.inpatient.department -> hospital_inpatient_department
  code, name_ar, name_en, main_specialty, ward_type, computed floor_count/bed_count
  M2one to hr.employee (manager_id, head_nurse_id)

- hospital.room -> hospital_room
  code, room_no, room_type, allowed_gender, capacity, room_status
  M2one to hospital.floor (required, restrict)
  computed department_id from floor_id.department_ids[0]

- hospital.bed -> hospital_bed
  code, bed_no, bed_status, allowed_gender, last_occupancy_date
  M2one to hospital.room (required, restrict), hospital.floor, hospital.inpatient.department,
  hospital.accommodation.grade, res.partner (current_patient_id)

### Clinical / visit flow

- saycare.visit -> saycare_visit
  name (seq), state (waiting -> triage -> doctor_queue -> in_progress -> done/cancelled),
  visit_type, financial_class, payment_method, basket_json, basket_paid,
  computed total_price/insurance_share/patient_share
  M2one to res.partner (required, restrict), saycare.specialty, hr.employee (doctor/nurse),
  account.move (invoice_id)
  O2M to medication orders, vital signs, clinical notes, lab/rad orders
  M2M to saycare.service via saycare_visit_service_rel

- saycare.appointment -> saycare_appointment
  name (seq), date, start_time/end_time, visit_type, state
  M2one to res.partner (required, restrict), hr.employee (doctor), saycare.specialty,
  saycare.visit (set null)

- saycare.clinical.note -> saycare_clinical_note
  chief_complaint, complaint_severity (1-10), diagnoses, JSON-text fields for symptoms/history
  M2one to saycare.visit (cascade), hr.employee (written_by)

- saycare.vital.signs -> saycare_vital_signs
  blood_pressure, temperature, pulse, respiratory_rate/type, o2_saturation, weight/height,
  computed bmi
  M2one to saycare.visit (cascade), hr.employee (recorded_by)

- saycare.lab.order -> saycare_lab_order
  test_name, test_code, priority, state, result_value/result_at
  M2one to saycare.visit (cascade), res.partner (restrict), hr.employee (requested_by)

- saycare.rad.order -> saycare_rad_order
  study_type, body_part, state, result_notes/result_at
  M2one to saycare.visit (cascade), res.partner (restrict), hr.employee (requested_by)

- saycare.medication.order -> saycare_medication_order
  drug_name, dose/frequency/duration, route, quantity, state (active/dispensed/cancelled/on_hold)
  M2one to saycare.visit (cascade), res.partner (restrict), product.product, uom.uom,
  hr.employee (prescribed/dispensed by), stock.picking (dispense_picking_id, set null)

### Admission / internal transfer requests

- saycare.admission.request -> saycare_admission_request
  Pending queue between OperationBookingPage / OPD and the قبول المريض (admission) screen.
  source (opd/operation_booking), status (pending_admission/admitted/cancelled)
  patient snapshot: patient_name, file_number, entry_permit_no, national_id, opd_visit_number,
    patient_mrn, patient_mobile, age, gender, address
  payment: payment_type, contract_entity, co_pay_percent, approval_required
  booking classification: is_inpatient, is_operation, transfer_type, operation_name/reason
  inpatient targets (set by OperationBookingPage): department_id, floor_id, stay_grade_id,
    room_id, bed_id
  clinical: diagnosis, reason, doctor_decision_notes, transfer_decision_reason, booking_datetime,
    surgeon_id/name, doctor_name, priority, anesthesia_type
  pre-admission planning: expected_admission_date/discharge_date, max_stay_days
  references: inpatient_booking_number, operation_booking_number (both from ir.sequence)
  admission-time only: ward, bed (Char snapshots, not FKs), attending_doctor, admission_date,
    admission_notes, admitted_at
  rejection-time only: rejection_reason, rejected_at
  M2one to res.partner, hospital.inpatient.department, hospital.floor,
  hospital.accommodation.grade (stay_grade_id), hospital.room, hospital.bed, hr.employee (surgeon_id)

### Patient background (long-lived, not visit-scoped)

- saycare.patient.allergy -> saycare_patient_allergy (allergen, reaction, severity)
- saycare.patient.condition -> saycare_patient_condition (name, icd_code, since_date)
- saycare.patient.surgery -> saycare_patient_surgery (procedure_name, procedure_date, hospital)
- saycare.patient.medication -> saycare_patient_medication (drug_name, dose, frequency, start_date)

All four: M2one to res.partner (required, cascade, domain is_patient=True).

### Catalog / specialty / staff

- saycare.specialty -> saycare_specialty
  name (uniq), code, room_number, color, consultant/specialist prices
  M2one to product.category (categ_id)
  O2M to hr.employee (doctor_ids), saycare.service (service_ids)

- saycare.service -> saycare_service
  name, code (uniq), visit_type, price, insurance_price
  M2one to product.template, saycare.specialty

- saycare.usage.type -> saycare_usage_type
  name (uniq); M2M from product.template via product_tmpl_usage_type_rel

- basket.model -> basket_model
  serial_no, barcode, planned_qty, price, computed total_price
  M2one to product.template (prod_id), product.product, uom.uom

- hr.employee (extended) -> hr_employee
  medical_role (doctor/nurse/receptionist/pharmacist/lab_tech/rad_tech), doctor_grade,
  license_number; M2one to saycare.specialty

### Geography (Egypt)

- saycare.governorate -> saycare_governorate
  name (uniq), region, capital, sequence
  O2M to saycare.city (city_ids)

- saycare.city -> saycare_city
  name, M2one to saycare.governorate (required, cascade) — مركز/حي under a governorate
  Seeded via data/saycare.governorate.csv and data/saycare.city.csv

### Refund workflow

- saycare.refund.request -> saycare_refund_request
  Pending queue: a doctor/nurse flags a visit's invoice for refund; treasury approves it
  (via the real refund flow in controllers/treasury.py) which deletes the pending request.
  patient_name, amount, reason, source (doctor/nurse)
  M2one to saycare.visit (required, cascade), account.move (invoice_id), res.partner

### Government expense module

- saycare.government.expense.decision -> saycare_government_expense_decision
  name, number, start_date, month_count, total_amount, deduction_amount, status,
  legacy *_json fallback fields, computed summary totals
  M2one to res.partner (restrict)
  O2M to clinic_ids, transaction_ids, allocation_ids
  M2M to product.template (scans/tests), saycare.specialty, product.category (medicine groups)

- saycare.gov.expense.clinic -> saycare_gov_expense_clinic
  line under a decision; M2one to decision (cascade), saycare.specialty
  M2M to saycare.service, product.template, product.product

- saycare.gov.expense.allocation -> saycare_gov_expense_allocation
  month_key, label, amount, addition, manual, computed used_amount/remaining/state_label
  M2one to decision (cascade)

- saycare.government.expense.transaction -> saycare_government_expense_transaction
  reference_no, date, item_type, amount, qty, parts_json, computed deducted
  M2one to decision (cascade)

- saycare.government.expense.settings -> saycare_government_expense_settings
  singleton: deduction_amount, max_addition_amount

## Extended existing Odoo models (columns added, no new table)

- res.partner: is_patient, patient_type, x_age_group (compute, not stored), mrn,
  x_entry_permit_no (unique, digits-only, renamed from entry_permit_no), id_type,
  id_number, name parts, dob, gender, home_phone, occupation, governorate, x_blood_type,
  financial_class, insurance_company, contract_entity, is_vendor)
- account.journal: financial_class
- account.move: financial_class (related to partner_id.financial_class, stored)
- insurance.company: provider_type
- product.pricelist: x_payment_type
- product.category: is_medicines, medicine_product_count (compute), categ_type, name_ar
- product.template: group_id, usage_type_ids (M2M), uom_small, forced_price (+currency),
  needs_refrigeration, storage_temp,
  similarity_type (legacy single-select) plus is_look_alike/is_sound_alike/
    is_high_concentration/is_hazardous (newer per-flag booleans, both kept side by side),
  generic_name, dosage_form, medicine_concentration, primary_route, secondary_route,
  atc_code, dispensing_category, usual_dose, max_daily_dose,
  pregnancy_category, lactation_use, pediatric_use,
  contraindications, special_warnings, side_effects, drug_interactions,
  uom_large/uom_medium (Char, legacy), uom_largee/uom_mediumm (M2one, uom.uom),
  categ_type (related), basket_table_id (O2M to basket.model), basket_service_id
- stock.move: q_sant
- stock.picking: state selection extended with quantities_confirmed, done

## Many2many relation tables

- hospital_floor_department_rel: hospital.floor <-> hospital.inpatient.department
- product_tmpl_usage_type_rel: product.template <-> saycare.usage.type
- saycare_visit_service_rel: saycare.visit <-> saycare.service
- gov_expense_clinic_service_rel: saycare.gov.expense.clinic <-> saycare.service
- gov_expense_clinic_product_svc_rel: saycare.gov.expense.clinic <-> product.template
- gov_expense_clinic_medicine_rel: saycare.gov.expense.clinic <-> product.product
- gov_expense_decision_scans_product_rel: decision <-> product.template (scans)
- gov_expense_decision_tests_product_rel: decision <-> product.template (tests)
- gov_expense_decision_specialty_rel: decision <-> saycare.specialty
- gov_expense_decision_medicine_categ_rel: decision <-> product.category (medicine groups)

