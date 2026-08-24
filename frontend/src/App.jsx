import { useEffect, useState } from 'react';
import { Link, Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import api from './services/api';

const roleLabels = {
  patient: 'Patient',
  doctor: 'Doctor',
  admin: 'Admin',
};

function AuthLayout({ children, logout, role }) {
  const routes = {
    patient: [
      { label: 'Dashboard', to: '/' },
      { label: 'Doctors', to: '/doctors' },
      { label: 'Appointments', to: '/appointments' },
    ],
    doctor: [
      { label: 'Dashboard', to: '/' },
      { label: 'Appointments', to: '/appointments' },
    ],
    admin: [
      { label: 'Dashboard', to: '/' },
      { label: 'Doctors', to: '/admin' },
    ],
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-block">
          <div className="brand-dot" />
          <span>Healthcare Manager</span>
        </div>
        <div className="user-tag">{roleLabels[role] || 'Portal'}</div>
        <nav className="nav-links">
          {(routes[role] || routes.patient).map((item) => (
            <Link key={item.to} to={item.to}>{item.label}</Link>
          ))}
          <button className="ghost-button" onClick={logout}>Logout</button>
        </nav>
      </header>
      <main className="page-container">{children}</main>
    </div>
  );
}

function LoginPage({ onLogin, onSwitchToRegister }) {
  const [form, setForm] = useState({ email: 'patient@example.com', password: 'Patient123!' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const response = await api.post('/auth/login', form);
      onLogin(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <p className="eyebrow">Healthcare portal</p>
        <h1>Welcome back</h1>
        <div className="credential-pills">
          <span>Patient: patient@example.com / Patient123!</span>
          <span>Doctor: doctor@example.com / Doctor123!</span>
          <span>Admin: admin@example.com / Admin123!</span>
        </div>
        <form onSubmit={submit} className="form-grid">
          <label>
            Email
            <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
          </label>
          <label>
            Password
            <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
          </label>
          {error && <div className="error-box">{error}</div>}
          <button type="submit" disabled={loading}>{loading ? 'Signing in...' : 'Login'}</button>
        </form>
        <p className="muted-link">
          Need an account? <button type="button" className="text-button" onClick={onSwitchToRegister}>Register</button>
        </p>
      </div>
    </div>
  );
}

function RegisterPage({ onRegister, onSwitchToLogin }) {
  const [form, setForm] = useState({ email: 'newpatient@example.com', password: 'Patient123!', full_name: 'New Patient' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const response = await api.post('/auth/register', form);
      onRegister(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <p className="eyebrow">Create account</p>
        <h1>Register as patient</h1>
        <form onSubmit={submit} className="form-grid">
          <label>
            Full name
            <input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required />
          </label>
          <label>
            Email
            <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
          </label>
          <label>
            Password
            <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
          </label>
          {error && <div className="error-box">{error}</div>}
          <button type="submit" disabled={loading}>{loading ? 'Creating account...' : 'Register'}</button>
        </form>
        <p className="muted-link">
          Already have an account? <button type="button" className="text-button" onClick={onSwitchToLogin}>Login</button>
        </p>
      </div>
    </div>
  );
}

function DoctorCard({ doctor, onSelect }) {
  return (
    <div className="doctor-card info-card">
      <div className="doctor-header">
        <img src={doctor.profile_photo_url || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=400&q=80'} alt={doctor.name} className="doctor-avatar" />
        <div>
          <p className="eyebrow">{doctor.specialization}</p>
          <h3>{doctor.name}</h3>
          <p>{doctor.qualification || 'Qualification not listed'}</p>
        </div>
      </div>
      <div className="doctor-meta">
        <span>{doctor.experience_years || 0} years</span>
        <span>{doctor.slot_duration_minutes || 30} min slots</span>
        <span>{doctor.status || 'available'}</span>
      </div>
      <p className="muted-text">{doctor.clinic_name || 'Primary care clinic'}</p>
      <button className="secondary-button" onClick={() => onSelect(doctor)}>View profile</button>
    </div>
  );
}

function PatientDashboard({ auth }) {
  const [doctors, setDoctors] = useState([]);
  const [selectedDoctor, setSelectedDoctor] = useState(null);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [slots, setSlots] = useState([]);
  const [selectedSlot, setSelectedSlot] = useState('');
  const [bookingStep, setBookingStep] = useState('select');
  const [bookingError, setBookingError] = useState('');
  const [symptomForm, setSymptomForm] = useState({
    chief_complaint: '',
    symptoms: '',
    duration: '2 days',
    severity: 'Medium',
    additional_notes: '',
  });
  const [summary, setSummary] = useState(null);
  const [bookingSuccess, setBookingSuccess] = useState(null);
  const [holdInfo, setHoldInfo] = useState(null);

  const formatShortDate = (value) => {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
  };

  const formatDisplayTime = (value) => {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
  };

  const fetchDoctors = async () => {
    try {
      const response = await api.get('/doctors');
      setDoctors(response.data || []);
    } catch {
      setDoctors([]);
    }
  };

  useEffect(() => {
    fetchDoctors();
  }, []);

  useEffect(() => {
    if (!selectedDoctor || !selectedDoctor.id) return;
    api.get(`/doctors/${selectedDoctor.id}/availability`, { params: { date: selectedDate } })
      .then((response) => {
        setSlots(response.data.slots || []);
        setSelectedSlot('');
      })
      .catch(() => setSlots([]));
  }, [selectedDoctor, selectedDate]);

  const openDoctorProfile = async (doctor) => {
    setBookingError('');
    setBookingSuccess(null);
    setSummary(null);
    setBookingStep('select');
    setSelectedDate(new Date().toISOString().split('T')[0]);
    setSelectedSlot('');
    setHoldInfo(null);
    setSymptomForm({
      chief_complaint: '',
      symptoms: '',
      duration: '2 days',
      severity: 'Medium',
      additional_notes: '',
    });

    try {
      const response = await api.get(`/doctors/${doctor.id}`);
      setSelectedDoctor({ ...doctor, ...response.data });
    } catch {
      setSelectedDoctor(doctor);
    }
  };

  const reserveSlot = async (slot) => {
    if (!selectedDoctor) return;
    setSelectedSlot(slot);
    setBookingError('');
    try {
      const response = await api.post('/appointments/hold', {
        doctor_id: selectedDoctor.id,
        start_time: slot,
      });
      setHoldInfo(response.data);
    } catch (error) {
      const detail = error.response?.data?.detail || 'Unable to reserve this slot right now.';
      setBookingError(detail);
    }
  };

  const startSymptomStep = () => {
    if (!selectedDoctor || !selectedSlot) {
      setBookingError('Please select an available appointment slot.');
      return;
    }
    setBookingError('');
    setSummary(null);
    setBookingStep('symptoms');
  };

  const continueToReview = () => {
    if (!symptomForm.chief_complaint || !symptomForm.symptoms) {
      setBookingError('Please enter your chief complaint and symptoms before continuing.');
      return;
    }
    setBookingError('');
    setBookingStep('review');
  };

  const confirmBooking = async () => {
    if (!selectedDoctor || !selectedSlot) {
      setBookingError('Please select an available slot before confirming.');
      return;
    }

    setBookingError('');
    setBookingStep('review');

    try {
      const response = await api.post('/appointments', {
        doctor_id: selectedDoctor.id,
        start_time: selectedSlot,
      });

      const appointment = response.data;
      try {
        const symptomResponse = await api.post(`/appointments/${appointment.id}/symptoms`, symptomForm);
        setSummary(symptomResponse.data.summary || { fallback: true, detail: { message: 'AI summary is currently unavailable. Your symptoms will still be saved for the doctor.' } });
      } catch (symptomError) {
        setSummary({
          fallback: true,
          detail: {
            message: 'AI summary is currently unavailable. Your symptoms will still be saved for the doctor.',
          },
        });
      }

      setBookingSuccess({
        id: appointment.id,
        doctor: selectedDoctor,
        start_time: appointment.start_time,
        date: selectedDate,
      });
      setBookingStep('success');
      setSelectedSlot('');
      setHoldInfo(null);
      setSlots([]);
    } catch (error) {
      const detail = error.response?.data?.detail || 'Unable to book the appointment right now. Please try again.';
      setBookingError(detail);
      setBookingStep('symptoms');
    }
  };

  const currentDoctorLeave = selectedDoctor?.leave_days?.length
    ? selectedDoctor.leave_days.find((leave) => leave.leave_date && leave.leave_date >= selectedDate)
    : null;

  return (
    <div>
      <div className="page-header">
        <div>
          <p className="eyebrow">Patient dashboard</p>
          <h1>Book your appointment</h1>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card"><span>Doctors</span><strong>{doctors.length}</strong></div>
        <div className="stat-card"><span>Follow-ups</span><strong>2</strong></div>
        <div className="stat-card"><span>Calendar sync</span><strong>Ready</strong></div>
      </div>

      <div className="card-list">
        {doctors.map((doctor) => (
          <DoctorCard key={doctor.id} doctor={doctor} onSelect={openDoctorProfile} />
        ))}
      </div>

      {selectedDoctor && (
        <div className="doctor-profile-overlay" onClick={() => setSelectedDoctor(null)}>
          <div className="doctor-profile-panel" onClick={(event) => event.stopPropagation()}>
            <div className="profile-header-row">
              <div className="doctor-header">
                <img src={selectedDoctor.profile_photo_url || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=400&q=80'} alt={selectedDoctor.name} className="doctor-avatar large" />
                <div>
                  <p className="eyebrow">{selectedDoctor.specialization}</p>
                  <h3>{selectedDoctor.name}</h3>
                  <p>{selectedDoctor.qualification || 'Qualification not listed'}</p>
                </div>
              </div>
              <button type="button" className="secondary-button" onClick={() => setSelectedDoctor(null)}>Close Profile</button>
            </div>

            <div className="doctor-meta">
              <span>{selectedDoctor.experience_years || 0} years experience</span>
              <span>{selectedDoctor.languages || 'English'}</span>
              <span>₹{selectedDoctor.consultation_fee || 0}</span>
              <span>{selectedDoctor.slot_duration_minutes || 30} min</span>
            </div>

            <p className="muted-text">{selectedDoctor.clinic_name || 'Clinic'}</p>
            <p>{selectedDoctor.bio || 'Experienced doctor focused on patient-first care.'}</p>

            {selectedDoctor.working_hours && selectedDoctor.working_hours.length > 0 && (
              <div className="profile-section">
                <h4>Working Hours</h4>
                <div className="working-hours-grid">
                  {Array.from({ length: 7 }, (_, index) => {
                    const dayHours = selectedDoctor.working_hours.filter((item) => item.weekday === index);
                    if (!dayHours.length) return null;
                    return (
                      <div key={index} className="schedule-day">
                        <strong>{['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][index]}</strong>
                        {dayHours.map((item) => (
                          <div key={`${index}-${item.start_time}-${item.end_time}`}>
                            {item.start_time} – {item.end_time}
                          </div>
                        ))}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {selectedDoctor.leave_days && selectedDoctor.leave_days.length > 0 && (
              <div className="profile-section">
                <h4>Leave Information</h4>
                <ul className="leave-list">
                  {selectedDoctor.leave_days.map((leave) => (
                    <li key={leave.id || leave.leave_date}>
                      {leave.leave_date} — {leave.reason || 'Doctor leave'}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {currentDoctorLeave && (
              <div className="info-box">Doctor is on leave on this date.</div>
            )}

            <div className="profile-section">
              <h4>Available Appointments</h4>
              <div className="booking-row">
                <label>
                  Select date
                  <input type="date" value={selectedDate} onChange={(e) => setSelectedDate(e.target.value)} />
                </label>
              </div>

              {bookingError && <div className="error-box">{bookingError}</div>}
              {holdInfo && <div className="info-box">Slot reserved for you for 5 minutes.</div>}

              <div className="slot-list">
                {slots.length === 0 ? (
                  <div className="info-box">No slots available for this date.</div>
                ) : (
                  slots.map((slot) => (
                    <button
                      key={slot}
                      type="button"
                      className={selectedSlot === slot ? 'slot-button selected' : 'slot-button'}
                      onClick={() => reserveSlot(slot)}
                    >
                      {formatDisplayTime(slot)}
                    </button>
                  ))
                )}
              </div>

              {selectedSlot && bookingStep === 'select' && (
                <div className="booking-actions">
                  <button className="primary-button" type="button" onClick={startSymptomStep}>Book Appointment</button>
                </div>
              )}
            </div>

            {bookingStep === 'symptoms' && (
              <div className="booking-panel symptom-step">
                <h3>Confirm Appointment</h3>
                <p><strong>Doctor:</strong> {selectedDoctor.name}</p>
                <p><strong>Date:</strong> {formatShortDate(selectedDate)}</p>
                <p><strong>Time:</strong> {formatDisplayTime(selectedSlot)}</p>
                <p>Before confirming your appointment, please describe your symptoms.</p>

                <div className="symptom-form">
                  <label>Chief complaint<input value={symptomForm.chief_complaint} onChange={(e) => setSymptomForm({ ...symptomForm, chief_complaint: e.target.value })} /></label>
                  <label>Symptoms<textarea value={symptomForm.symptoms} onChange={(e) => setSymptomForm({ ...symptomForm, symptoms: e.target.value })} /></label>
                  <label>Duration<input value={symptomForm.duration} onChange={(e) => setSymptomForm({ ...symptomForm, duration: e.target.value })} /></label>
                  <label>Severity<select value={symptomForm.severity} onChange={(e) => setSymptomForm({ ...symptomForm, severity: e.target.value })}><option>Low</option><option>Medium</option><option>High</option></select></label>
                  <label>Additional notes<textarea value={symptomForm.additional_notes} onChange={(e) => setSymptomForm({ ...symptomForm, additional_notes: e.target.value })} /></label>
                </div>

                <div className="booking-actions">
                  <button className="secondary-button" type="button" onClick={() => setBookingStep('select')}>Cancel</button>
                  <button className="primary-button" type="button" onClick={continueToReview}>Continue</button>
                </div>
              </div>
            )}

            {bookingStep === 'review' && (
              <div className="booking-panel symptom-step">
                <h3>Appointment Summary</h3>
                <p><strong>Doctor:</strong> {selectedDoctor.name}</p>
                <p><strong>Date:</strong> {formatShortDate(selectedDate)}</p>
                <p><strong>Time:</strong> {formatDisplayTime(selectedSlot)}</p>
                <p><strong>Symptoms:</strong> {symptomForm.symptoms}</p>
                {summary && summary.fallback ? (
                  <div className="info-box">AI summary is currently unavailable. Your symptoms will still be saved for the doctor.</div>
                ) : summary ? (
                  <div>
                    <p><strong>AI Pre-Visit Summary:</strong></p>
                    <p><strong>Urgency:</strong> {summary.detail?.urgency_level || summary.urgency_level || 'Unavailable'}</p>
                    <p>{summary.detail?.message || summary.message || 'Summary captured successfully.'}</p>
                  </div>
                ) : (
                  <div className="info-box">Your symptoms will be saved and an AI summary will be generated if available.</div>
                )}

                <div className="booking-actions">
                  <button className="secondary-button" type="button" onClick={() => setBookingStep('symptoms')}>Go Back</button>
                  <button className="primary-button" type="button" onClick={confirmBooking}>Confirm Appointment</button>
                </div>
              </div>
            )}

            {bookingStep === 'success' && bookingSuccess && (
              <div className="booking-panel success-box">
                <h3>Appointment Confirmed ✓</h3>
                <p>Your appointment has been successfully booked.</p>
                <p><strong>Doctor:</strong> {bookingSuccess.doctor.name}</p>
                <p><strong>Date:</strong> {formatShortDate(bookingSuccess.start_time || bookingSuccess.date)}</p>
                <p><strong>Time:</strong> {formatDisplayTime(bookingSuccess.start_time)}</p>
                <p><strong>Appointment ID:</strong> {bookingSuccess.id}</p>

                <div className="booking-actions">
                  <button className="primary-button" type="button" onClick={() => setSelectedDoctor(null)}>Back to Doctors</button>
                  <button className="secondary-button" type="button" onClick={() => window.location.hash = '#appointments'}>View My Appointments</button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function DoctorDashboard() {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [notes, setNotes] = useState({});
  const [summaries, setSummaries] = useState({});

  useEffect(() => {
    api.get('/appointments').then((response) => setAppointments(response.data)).catch(() => setAppointments([])).finally(() => setLoading(false));
  }, []);

  const saveNote = async (id) => {
    const payload = notes[id] || { note_text: 'Follow-up with patient after review.', diagnosis: 'Monitoring and follow up' };
    await api.post(`/appointments/${id}/clinical-notes`, payload);
  };

  const saveSummary = async (id) => {
    const payload = summaries[id] || { summary: 'Patient advised to continue rest and monitor symptoms.', medication_schedule: [{ medicine: 'Paracetamol', dosage: '500mg', frequency: 'Twice daily', instructions: 'After meals' }], follow_up_steps: ['Reassess in 7 days', 'Return if fever persists'] };
    await api.post(`/appointments/${id}/post-visit-summary`, payload);
  };

  return (
    <div>
      <div className="page-header"><div><p className="eyebrow">Doctor portal</p><h1>Upcoming appointments</h1></div></div>
      {loading ? <div className="info-box">Loading appointments...</div> : appointments.map((appointment) => (
        <div key={appointment.id} className="info-card booking-panel">
          <h3>{appointment.id}</h3>
          <p>{appointment.start_time}</p>
          <p>Status: {appointment.status}</p>

          <div className="symptom-form">
            <h4>Clinical notes</h4>
            <textarea value={notes[appointment.id]?.note_text || 'Patient reviewed; moderate symptoms persist.'} onChange={(e) => setNotes({ ...notes, [appointment.id]: { ...(notes[appointment.id] || {}), note_text: e.target.value } })} />
            <input value={notes[appointment.id]?.diagnosis || 'Follow up review'} onChange={(e) => setNotes({ ...notes, [appointment.id]: { ...(notes[appointment.id] || {}), diagnosis: e.target.value } })} />
            <button onClick={() => saveNote(appointment.id)}>Save clinical note</button>
          </div>

          <div className="symptom-form">
            <h4>Post-visit summary</h4>
            <textarea value={summaries[appointment.id]?.summary || 'Patient advised to continue rest and monitor symptoms.'} onChange={(e) => setSummaries({ ...summaries, [appointment.id]: { ...(summaries[appointment.id] || {}), summary: e.target.value } })} />
            <button onClick={() => saveSummary(appointment.id)}>Generate patient-friendly summary</button>
          </div>
        </div>
      ))}
    </div>
  );
}

function AdminPanel() {
  const [doctors, setDoctors] = useState([]);
  const [doctorForm, setDoctorForm] = useState({ email: 'newdoctor@example.com', password: 'Doctor123!', full_name: 'Dr. Emma Brooks', specialization: 'Neurology', qualification: 'MD Neurology', experience_years: 7, slot_duration_minutes: 30 });
  const [leaveDate, setLeaveDate] = useState('');
  const [leaveReason, setLeaveReason] = useState('Annual leave');

  const loadDoctors = () => {
    api.get('/admin/doctors').then((response) => setDoctors(response.data)).catch(() => setDoctors([]));
  };

  useEffect(() => loadDoctors(), []);

  const createDoctor = async () => {
    await api.post('/admin/doctors', doctorForm);
    loadDoctors();
  };

  const addLeave = async (doctorId) => {
    await api.post(`/admin/doctors/${doctorId}/leave`, { leave_date: leaveDate, reason: leaveReason });
    loadDoctors();
  };

  return (
    <div>
      <div className="page-header"><div><p className="eyebrow">Admin</p><h1>Doctor management</h1></div></div>
      <div className="booking-panel">
        <h3>Create doctor profile</h3>
        <div className="symptom-form">
          <label>Email<input value={doctorForm.email} onChange={(e) => setDoctorForm({ ...doctorForm, email: e.target.value })} /></label>
          <label>Password<input type="password" value={doctorForm.password} onChange={(e) => setDoctorForm({ ...doctorForm, password: e.target.value })} /></label>
          <label>Full name<input value={doctorForm.full_name} onChange={(e) => setDoctorForm({ ...doctorForm, full_name: e.target.value })} /></label>
          <label>Specialization<input value={doctorForm.specialization} onChange={(e) => setDoctorForm({ ...doctorForm, specialization: e.target.value })} /></label>
          <label>Qualification<input value={doctorForm.qualification} onChange={(e) => setDoctorForm({ ...doctorForm, qualification: e.target.value })} /></label>
          <label>Experience years<input type="number" value={doctorForm.experience_years} onChange={(e) => setDoctorForm({ ...doctorForm, experience_years: Number(e.target.value) })} /></label>
          <button onClick={createDoctor}>Create doctor</button>
        </div>
      </div>

      <div className="card-list">
        {doctors.map((doctor) => (
          <div key={doctor.id} className="info-card">
            <h3>{doctor.name}</h3>
            <p>{doctor.specialization}</p>
            <label>Leave date<input type="date" value={leaveDate} onChange={(e) => setLeaveDate(e.target.value)} /></label>
            <label>Reason<input value={leaveReason} onChange={(e) => setLeaveReason(e.target.value)} /></label>
            <button className="secondary-button" onClick={() => addLeave(doctor.id)}>Mark leave</button>
          </div>
        ))}
      </div>
    </div>
  );
}

function AppointmentsPage({ auth }) {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedAppointment, setSelectedAppointment] = useState(null);
  const [details, setDetails] = useState(null);
  const [rescheduleDate, setRescheduleDate] = useState('');
  const [rescheduleSlots, setRescheduleSlots] = useState([]);
  const [selectedRescheduleSlot, setSelectedRescheduleSlot] = useState('');

  const formatDateLabel = (value) => {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  };

  const formatTimeRange = (start, end) => {
    if (!start || !end) return '';
    const startDate = new Date(start);
    const endDate = new Date(end);
    if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) return '';
    return `${startDate.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })} – ${endDate.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })}`;
  };

  const statusMeta = {
    CONFIRMED: { label: 'Confirmed', tone: 'success' },
    COMPLETED: { label: 'Completed', tone: 'secondary' },
    CANCELLED: { label: 'Cancelled', tone: 'danger' },
    RESCHEDULED: { label: 'Rescheduled', tone: 'info' },
    DOCTOR_LEAVE: { label: 'Doctor on Leave', tone: 'warning' },
    PENDING: { label: 'Pending', tone: 'secondary' },
  };

  const loadAppointments = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await api.get('/appointments');
      setAppointments(response.data || []);
    } catch {
      setAppointments([]);
      setError('Unable to load your appointments. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAppointments();
  }, []);

  const openDetails = async (appointment) => {
    try {
      const response = await api.get(`/appointments/${appointment.id}`);
      setDetails(response.data);
      setSelectedAppointment(appointment);
    } catch {
      setDetails(appointment);
      setSelectedAppointment(appointment);
    }
  };

  const handleCancel = async (appointment) => {
    const confirmed = window.confirm(`Are you sure you want to cancel your appointment with ${appointment.doctor?.name || 'your doctor'} on ${formatDateLabel(appointment.start_time)} at ${formatTimeRange(appointment.start_time, appointment.end_time)}?`);
    if (!confirmed) return;
    try {
      await api.post(`/appointments/${appointment.id}/cancel`);
      await loadAppointments();
      setSelectedAppointment(null);
      setDetails(null);
    } catch {
      setError('Unable to cancel this appointment right now. Please try again.');
    }
  };

  const startReschedule = async (appointment) => {
    const nextDate = appointment.start_time ? new Date(appointment.start_time).toISOString().split('T')[0] : '';
    setSelectedAppointment(appointment);
    setDetails(null);
    setRescheduleDate(nextDate);
    if (appointment.doctor?.id) {
      try {
        const response = await api.get(`/doctors/${appointment.doctor.id}/availability`, { params: { date: nextDate } });
        setRescheduleSlots(response.data.slots || []);
      } catch {
        setRescheduleSlots([]);
      }
    }
  };

  const onRescheduleDateChange = async (date) => {
    setRescheduleDate(date);
    const current = selectedAppointment;
    if (!current?.doctor?.id) return;
    try {
      const response = await api.get(`/doctors/${current.doctor.id}/availability`, { params: { date } });
      setRescheduleSlots(response.data.slots || []);
    } catch {
      setRescheduleSlots([]);
    }
    setSelectedRescheduleSlot('');
  };

  const submitReschedule = async () => {
    if (!selectedAppointment || !selectedRescheduleSlot) return;
    try {
      await api.patch(`/appointments/${selectedAppointment.id}/reschedule`, { start_time: selectedRescheduleSlot });
      await loadAppointments();
      setSelectedAppointment(null);
      setDetails(null);
      setRescheduleDate('');
      setRescheduleSlots([]);
      setSelectedRescheduleSlot('');
    } catch (error) {
      setError(error.response?.data?.detail || 'Unable to reschedule this appointment. Please try again.');
    }
  };

  const upcomingAppointments = appointments.filter((appointment) => new Date(appointment.start_time) >= new Date());
  const pastAppointments = appointments.filter((appointment) => new Date(appointment.start_time) < new Date());

  const renderAppointmentCard = (appointment) => {
    const doctor = appointment.doctor || {};
    const meta = statusMeta[appointment.status] || { label: appointment.status, tone: 'secondary' };
    return (
      <div key={appointment.id} className="appointment-card">
        <div className="appointment-card-header">
          <div className="doctor-header compact">
            <img src={doctor.photo || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=400&q=80'} alt={doctor.name || 'Doctor'} className="doctor-avatar small" />
            <div>
              <h3>{doctor.name || 'Doctor'}</h3>
              <p>{doctor.specialization || 'Specialist'}</p>
              <p className="muted-text">{doctor.qualification || 'Qualification not listed'}</p>
            </div>
          </div>
          <span className={`status-badge ${meta.tone}`}>{meta.label}</span>
        </div>

        <div className="appointment-meta-block">
          <div><strong>📅</strong> {formatDateLabel(appointment.start_time)}</div>
          <div><strong>🕐</strong> {formatTimeRange(appointment.start_time, appointment.end_time)}</div>
          <div><strong>📍</strong> {doctor.clinic || appointment.clinic || 'Clinic address unavailable'}</div>
        </div>

        <div className="appointment-actions">
          <button className="secondary-button" onClick={() => openDetails(appointment)}>View Details</button>
          <button className="secondary-button" onClick={() => startReschedule(appointment)}>Reschedule</button>
          <button className="danger-button" onClick={() => handleCancel(appointment)}>Cancel Appointment</button>
        </div>
      </div>
    );
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <p className="eyebrow">Appointments</p>
          <h1>{roleLabels[auth?.user?.role] || 'Appointments'}</h1>
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}

      {loading ? (
        <div className="info-box">Loading appointments...</div>
      ) : appointments.length === 0 ? (
        <div className="empty-state">
          <h3>No appointments yet</h3>
          <p>Find a doctor and book your first appointment.</p>
          <button className="primary-button" type="button" onClick={() => window.location.href = '/doctors'}>Find a Doctor</button>
        </div>
      ) : (
        <>
          <section className="appointments-section">
            <h2>Upcoming Appointments</h2>
            <div className="card-list">
              {upcomingAppointments.length === 0 ? <div className="info-box">You don't have any upcoming appointments.</div> : upcomingAppointments.map(renderAppointmentCard)}
            </div>
          </section>

          {pastAppointments.length > 0 && (
            <section className="appointments-section">
              <h2>Past Appointments</h2>
              <div className="card-list">
                {pastAppointments.map(renderAppointmentCard)}
              </div>
            </section>
          )}
        </>
      )}

      {selectedAppointment && !rescheduleDate && (
        <div className="doctor-profile-overlay" onClick={() => { setSelectedAppointment(null); setDetails(null); }}>
          <div className="doctor-profile-panel" onClick={(event) => event.stopPropagation()}>
            <div className="profile-header-row">
              <h3>Appointment Details</h3>
              <button type="button" className="secondary-button" onClick={() => { setSelectedAppointment(null); setDetails(null); }}>Close</button>
            </div>

            {(details || selectedAppointment) && (() => {
              const current = details || selectedAppointment;
              const doctor = current.doctor || {};
              const status = statusMeta[current.status] || { label: current.status, tone: 'secondary' };
              return (
                <div>
                  <div className="doctor-header compact">
                    <img src={doctor.photo || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=400&q=80'} alt={doctor.name || 'Doctor'} className="doctor-avatar small" />
                    <div>
                      <h3>{doctor.name || 'Doctor'}</h3>
                      <p>{doctor.specialization || 'Specialist'}</p>
                      <p>{doctor.qualification || 'Qualification not listed'}</p>
                    </div>
                  </div>

                  <div className="appointment-meta-block">
                    <div><strong>Clinic:</strong> {doctor.clinic || current.clinic || 'Clinic address unavailable'}</div>
                    <div><strong>Date:</strong> {formatDateLabel(current.start_time)}</div>
                    <div><strong>Time:</strong> {formatTimeRange(current.start_time, current.end_time)}</div>
                    <div><strong>Status:</strong> <span className={`status-badge ${status.tone}`}>{status.label}</span></div>
                  </div>

                  <div className="profile-section">
                    <h4>Symptoms submitted</h4>
                    {current.symptoms && current.symptoms.length > 0 ? (
                      current.symptoms.map((symptom) => (
                        <div key={symptom.id} className="symptom-note">
                          <p><strong>Chief complaint:</strong> {symptom.chief_complaint || 'Not provided'}</p>
                          <p><strong>Symptoms:</strong> {symptom.symptoms || 'Not provided'}</p>
                          <p><strong>Severity:</strong> {symptom.severity || 'Not provided'}</p>
                        </div>
                      ))
                    ) : (
                      <p>No symptoms submitted yet.</p>
                    )}
                  </div>

                  <div className="profile-section">
                    <h4>Pre-visit AI Summary</h4>
                    {current.pre_visit_summary ? (
                      <div>
                        <p><strong>Chief Complaint:</strong> {current.pre_visit_summary.chief_complaint || 'Not available'}</p>
                        <p><strong>Urgency:</strong> {current.pre_visit_summary.urgency_level || 'Not available'}</p>
                        <ul>
                          {(current.pre_visit_summary.suggested_questions || []).map((question) => <li key={question}>{question}</li>)}
                        </ul>
                      </div>
                    ) : (
                      <p>AI summary is currently unavailable. Your submitted symptoms are still available to the doctor.</p>
                    )}
                  </div>

                  <div className="appointment-actions">
                    <button className="secondary-button" onClick={() => startReschedule(current)}>Reschedule</button>
                    <button className="danger-button" onClick={() => handleCancel(current)}>Cancel Appointment</button>
                  </div>
                </div>
              );
            })()}
          </div>
        </div>
      )}

      {selectedAppointment && rescheduleDate && (
        <div className="doctor-profile-overlay" onClick={() => { setSelectedAppointment(null); setRescheduleDate(''); setSelectedRescheduleSlot(''); setRescheduleSlots([]); }}>
          <div className="doctor-profile-panel" onClick={(event) => event.stopPropagation()}>
            <div className="profile-header-row">
              <h3>Reschedule Appointment</h3>
              <button type="button" className="secondary-button" onClick={() => { setSelectedAppointment(null); setRescheduleDate(''); setSelectedRescheduleSlot(''); setRescheduleSlots([]); }}>Close</button>
            </div>
            <div className="profile-section">
              <label>
                Select a new date
                <input type="date" value={rescheduleDate} onChange={(e) => onRescheduleDateChange(e.target.value)} />
              </label>
            </div>
            <div className="slot-list">
              {rescheduleSlots.length === 0 ? (
                <div className="info-box">No new slots available for this date.</div>
              ) : (
                rescheduleSlots.map((slot) => (
                  <button key={slot} type="button" className={selectedRescheduleSlot === slot ? 'slot-button selected' : 'slot-button'} onClick={() => setSelectedRescheduleSlot(slot)}>
                    {new Date(slot).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })}
                  </button>
                ))
              )}
            </div>
            <div className="appointment-actions">
              <button className="secondary-button" type="button" onClick={() => { setRescheduleDate(''); setSelectedRescheduleSlot(''); setRescheduleSlots([]); }}>Cancel</button>
              <button className="primary-button" type="button" onClick={submitReschedule} disabled={!selectedRescheduleSlot}>Confirm Reschedule</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function AppContent({ auth, setAuth }) {
  const navigate = useNavigate();

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setAuth(null);
    navigate('/login');
  };

  if (!auth) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage onLogin={(data) => { localStorage.setItem('token', data.access_token); localStorage.setItem('user', JSON.stringify({ id: data.user_id, role: data.role })); setAuth({ ...data, token: data.access_token, user: { role: data.role, id: data.user_id } }); navigate('/'); }} onSwitchToRegister={() => navigate('/register')} />} />
        <Route path="/register" element={<RegisterPage onRegister={(data) => { localStorage.setItem('token', data.access_token); localStorage.setItem('user', JSON.stringify({ id: data.user_id, role: data.role })); setAuth({ ...data, token: data.access_token, user: { role: data.role, id: data.user_id } }); navigate('/'); }} onSwitchToLogin={() => navigate('/login')} />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  const role = auth.user?.role || auth.role;

  return (
    <AuthLayout logout={logout} role={role}>
      <Routes>
        <Route path="/" element={role === 'doctor' ? <DoctorDashboard /> : role === 'admin' ? <AdminPanel /> : <PatientDashboard auth={auth} />} />
        <Route path="/doctors" element={<PatientDashboard auth={auth} />} />
        <Route path="/appointments" element={<AppointmentsPage auth={auth} />} />
        <Route path="/admin" element={<AdminPanel />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthLayout>
  );
}

export default function App() {
  const [auth, setAuth] = useState(() => {
    const token = localStorage.getItem('token');
    const storedUser = localStorage.getItem('user');
    if (!token || !storedUser) return null;
    try {
      return { token, user: JSON.parse(storedUser) };
    } catch {
      return null;
    }
  });

  return <AppContent auth={auth} setAuth={setAuth} />;
}
