export type UserRole = 'patient' | 'provider' | 'nurse' | 'admin' | 'lab_tech' | 'pharmacist' | 'public_health' | 'records_officer' | 'medical_records' | 'clinical_officer' | 'receptionist';

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  phone?: string;
  facility_id?: string;
  specialty?: string;
  license_number?: string;
  avatar_url?: string;
  preferred_language: string;
  email_verified: boolean;
  mfa_enabled: boolean;
  created_at: string;
}

export interface Patient {
  id: string;
  user_id: string;
  name: string;
  date_of_birth: string;
  gender: 'male' | 'female' | 'other';
  phone?: string;
  address?: string;
  district?: string;
  province?: string;
  national_id?: string;
  emergency_contact?: string;
  blood_type?: string;
  allergies?: string[];
  chronic_conditions?: string[];
  nupn?: string;
  created_at: string;
}

export interface Appointment {
  id: string;
  patient_id: string;
  provider_id: string;
  facility_id: string;
  appointment_type: 'in-person' | 'telemedicine' | 'home-visit';
  status: 'scheduled' | 'confirmed' | 'in-progress' | 'completed' | 'cancelled' | 'no-show';
  start_time: string;
  end_time: string;
  reason?: string;
  notes?: string;
  patient?: Patient;
  created_at: string;
}

export interface VitalSign {
  id: string;
  patient_id: string;
  blood_pressure_systolic: number;
  blood_pressure_diastolic: number;
  heart_rate: number;
  respiratory_rate: number;
  temperature: number;
  oxygen_saturation: number;
  weight?: number;
  height?: number;
  bmi?: number;
  pain_level?: number;
  recorded_at: string;
  recorded_by: string;
}

export interface Medication {
  id: string;
  patient_id: string;
  name: string;
  dosage: string;
  frequency: string;
  route: string;
  start_date: string;
  end_date?: string;
  prescribed_by: string;
  pharmacy_id?: string;
  status: 'active' | 'completed' | 'discontinued' | 'on-hold';
  refill_remaining?: number;
  last_refill_date?: string;
}

export interface LabResult {
  id: string;
  patient_id: string;
  test_name: string;
  test_category: string;
  result: string;
  reference_range: string;
  unit: string;
  status: 'pending' | 'in-progress' | 'completed' | 'cancelled';
  is_critical: boolean;
  ordered_by: string;
  performed_by?: string;
  ordered_at: string;
  completed_at?: string;
  notes?: string;
}

export interface Encounter {
  id: string;
  patient_id: string;
  provider_id: string;
  facility_id: string;
  encounter_type: string;
  chief_complaint?: string;
  diagnosis?: string;
  icd_codes?: string[];
  notes?: string;
  soap_note?: SoapNote;
  started_at: string;
  ended_at?: string;
}

export interface SoapNote {
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
  ai_suggested?: string;
}

export interface Facility {
  id: string;
  name: string;
  type: 'hospital' | 'clinic' | 'health_post' | 'pharmacy';
  district: string;
  province: string;
  latitude?: number;
  longitude?: number;
  phone?: string;
  beds_total: number;
  beds_available: number;
  ambulance_available: boolean;
}

export interface BedOccupancy {
  facility_id: string;
  department: string;
  total_beds: number;
  occupied_beds: number;
  available_beds: number;
  occupancy_rate: number;
  updated_at: string;
}

export interface DiseaseAlert {
  id: string;
  disease: string;
  district: string;
  province: string;
  cases_reported: number;
  severity: 'low' | 'moderate' | 'high' | 'critical';
  status: 'active' | 'investigating' | 'contained';
  reported_at: string;
  notes?: string;
}

export interface TelemedicineSession {
  id: string;
  patient_id: string;
  provider_id: string;
  status: 'waiting' | 'active' | 'completed' | 'missed';
  start_time?: string;
  end_time?: string;
  signal_quality?: 'excellent' | 'good' | 'fair' | 'poor';
  notes?: string;
}

export interface PharmacyStock {
  id: string;
  medication_name: string;
  generic_name: string;
  category: string;
  quantity: number;
  unit: string;
  reorder_level: number;
  expiry_date: string;
  supplier?: string;
  cost_per_unit: number;
  selling_price: number;
  batch_number?: string;
}

export interface StaffMember {
  id: string;
  user_id: string;
  name: string;
  role: string;
  department: string;
  schedule?: ScheduleShift[];
  is_online: boolean;
}

export interface ScheduleShift {
  date: string;
  start_time: string;
  end_time: string;
  department: string;
}

export interface HealthEducationResource {
  id: string;
  title: string;
  description: string;
  category: string;
  language: string;
  content_url?: string;
  video_url?: string;
  is_offline_available: boolean;
  target_audience: string[];
}

export interface FinancialSummary {
  period: string;
  revenue: number;
  expenses: number;
  net_income: number;
  currency: 'ZMW';
  department_breakdown?: Record<string, number>;
}

export interface QueueEntry {
  id: string;
  patient_id: string;
  patient_name: string;
  priority: 'emergency' | 'urgent' | 'normal';
  status: 'waiting' | 'triage' | 'with-provider' | 'completed';
  check_in_time: string;
  estimated_wait_minutes: number;
  department: string;
}

export type JourneyPriority = 'emergency' | 'urgent' | 'routine';
export type JourneyStatus = 'waiting' | 'in_progress' | 'completed' | 'cancelled';
export type PaymentScheme =
  | 'cash'
  | 'nhima'
  | 'prudential'
  | 'sanlam'
  | 'madison'
  | 'jubilee'
  | 'employer'
  | 'other';
export type VisitType = 'new' | 'review';
export type VisitPaymentStatus = 'paid' | 'unpaid';
export type FlowStepType =
  | 'registration'
  | 'triage'
  | 'consultation'
  | 'laboratory'
  | 'pharmacy'
  | 'imaging'
  | 'procedure'
  | 'admission'
  | 'cashier'
  | 'referral'
  | 'discharge'
  | 'other';
export type FlowStepStatus = 'waiting' | 'called' | 'in_progress' | 'completed' | 'skipped' | 'cancelled';
export type FlowStepOutcome =
  | 'completed'
  | 'referred'
  | 'admitted'
  | 'discharged'
  | 'left_without_being_seen'
  | 'no_show'
  | 'cancelled';

export interface FlowPatientSummary {
  id: string;
  first_name: string;
  last_name: string;
  nrc_number?: string | null;
  phone?: string | null;
}

export interface JourneyStep {
  id: string;
  journey_id: string;
  step_number: number;
  step_type: FlowStepType;
  service_point: string;
  status: FlowStepStatus;
  priority: JourneyPriority;
  outcome?: FlowStepOutcome | null;
  department_id?: string | null;
  department_name?: string | null;
  provider_id?: string | null;
  provider_name?: string | null;
  queue_position?: number | null;
  reason?: string | null;
  notes?: string | null;
  referred_to_step_type?: FlowStepType | null;
  referred_to_service_point?: string | null;
  referred_to_department_id?: string | null;
  referred_to_provider_id?: string | null;
  called_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at?: string | null;
}

export interface PatientJourney {
  id: string;
  hospital_id: string;
  patient_id: string;
  encounter_id?: string | null;
  journey_number: string;
  status: JourneyStatus;
  priority: JourneyPriority;
  payment_scheme: PaymentScheme;
  visit_type: VisitType;
  payment_status: VisitPaymentStatus;
  scheme_number?: string | null;
  chief_complaint?: string | null;
  arrival_notes?: string | null;
  current_step_id?: string | null;
  current_step_type?: FlowStepType | null;
  current_service_point?: string | null;
  current_department_id?: string | null;
  current_department_name?: string | null;
  current_provider_id?: string | null;
  current_provider_name?: string | null;
  checked_in_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  closed_reason?: string | null;
  created_at: string;
  updated_at?: string | null;
  patient?: FlowPatientSummary | null;
  steps: JourneyStep[];
}

export interface FlowQueueItem {
  step_id: string;
  journey_id: string;
  journey_number: string;
  patient_id: string;
  patient_name: string;
  nrc_number?: string | null;
  phone?: string | null;
  priority: JourneyPriority;
  status: FlowStepStatus;
  step_type: FlowStepType;
  service_point: string;
  department_id?: string | null;
  department_name?: string | null;
  provider_id?: string | null;
  provider_name?: string | null;
  payment_scheme: PaymentScheme;
  visit_type: VisitType;
  payment_status: VisitPaymentStatus;
  scheme_number?: string | null;
  position: number;
  wait_minutes: number;
  reason?: string | null;
  checked_in_at: string;
  created_at: string;
}

export interface FlowQueueResponse {
  items: FlowQueueItem[];
  total: number;
}

export interface FlowStats {
  waiting: number;
  called: number;
  in_progress: number;
  active_total: number;
  completed_today: number;
  by_priority: Record<string, number>;
  by_service_point: Record<string, number>;
  average_wait_minutes: number;
  longest_wait_minutes: number;
}

export interface DestinationDepartment {
  id: string;
  name: string;
  code?: string | null;
  location?: string | null;
}

export interface DestinationStaff {
  id: string;
  user_id?: string | null;
  name: string;
  role: string;
  speciality?: string | null;
  department_id?: string | null;
  department_name?: string | null;
}

export interface ServicePointOption {
  code: string;
  label: string;
  step_type: FlowStepType;
}

export interface FlowDestinations {
  departments: DestinationDepartment[];
  staff: DestinationStaff[];
  service_points: ServicePointOption[];
}

// ─── Hospital directory (admin) ───────────────────────────────────────────────
export type HospitalStaffRole =
  | 'doctor'
  | 'nurse'
  | 'midwife'
  | 'clinical_officer'
  | 'pharmacist'
  | 'lab_technician'
  | 'radiographer'
  | 'administrator'
  | 'accountant'
  | 'records_officer'
  | 'community_health_worker'
  | 'cleaner'
  | 'security';

export interface HospitalDepartment {
  id: string;
  name: string;
  code?: string | null;
  head_of_department?: string | null;
  location?: string | null;
  phone_extension?: string | null;
  is_active: boolean;
}

export interface HospitalStaff {
  id: string;
  user_id?: string | null;
  first_name: string;
  last_name: string;
  role: HospitalStaffRole;
  speciality?: string | null;
  department_id?: string | null;
  phone?: string | null;
  email?: string | null;
  license_number?: string | null;
  is_active: boolean;
  max_hours_per_week: number;
}

export interface PatientSearchResult {
  id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
  phone: string;
  nrc_number?: string | null;
  province?: string | null;
  address_line?: string | null;
  city?: string | null;
  insurance_provider?: string | null;
  insurance_number?: string | null;
  nhima_member?: boolean;
  nhima_number?: string | null;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, string[]>;
}

export interface WebSocketMessage {
  type: string;
  payload: Record<string, unknown>;
  timestamp: string;
}
