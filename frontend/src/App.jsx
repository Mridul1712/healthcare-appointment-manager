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
  const [form, setForm] = useState({ email: 'patient@example.com', password: 'secret123' });
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
          <span>Patient: patient@example.com / secret123</span>
          <span>Doctor: doctor@example.com / doctor123</span>
          <span>Admin: admin@example.com / admin123</span>
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
  const [form, setForm] = useState({ email: 'newpatient@example.com', password: 'secret123', full_name: 'New Patient' });
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
      <div>
        <p className="eyebrow">{doctor.specialization}</p>
        <h3>{doctor.name}</h3>
        <p>{doctor.qualification || 'Qualification not listed'}</p>
      </div>
      <div className="doctor-meta">
        <span>{doctor.experience_years || 0} years</span>
        <span>{doctor.slot_duration_minutes || 30} min slots</span>
      </div>
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
  const [bookingSummary, setBookingSummary] = useState(null);
  const [symptomForm, setSymptomForm] = useState({ chief_complaint: 'Fever', symptoms: 'Body ache and mild cough', duration: '2 days', severity: 'Medium', additional_notes: 'Worse in evenings' });
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    api.get('/doctors').then((response) => setDoctors(response.data)).catch(() => setDoctors([]));
  }, []);

  useEffect(() => {
    if (!selectedDoctor) return;
    api.get(`/doctors/${selectedDoctor.id}/availability`, { params: { date: selectedDate } })
      .then((response) => {
        setSlots(response.data.slots || []);
        setSelectedSlot('');
      })
      .catch(() => setSlots([]));
  }, [selectedDoctor, selectedDate]);

  const bookAppointment = async () => {
    if (!selectedDoctor || !selectedSlot) return;
    const appointmentTime = new Date(`${selectedDate}T${selectedSlot}:00`).toISOString();
    try {
      const response = await api.post('/appointments', { doctor_id: selectedDoctor.id, start_time: appointmentTime });
      setBookingSummary(response.data);
      setSummary(null);
    } catch (error) {
      setBookingSummary({ error: error.response?.data?.detail || 'Slot is no longer available.' });
    }
  };

  const submitSymptoms = async () => {
    if (!bookingSummary || bookingSummary.error) return;
    const response = await api.post(`/appointments/${bookingSummary.id}/symptoms`, symptomForm);
    const detail = await api.get(`/appointments/${bookingSummary.id}/pre-visit-summary`);
    setSummary({ ...response.data, detail: detail.data });
  };

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
          <DoctorCard key={doctor.id} doctor={doctor} onSelect={setSelectedDoctor} />
        ))}
      </div>

      {selectedDoctor && (
        <div className="booking-panel">
          <h3>{selectedDoctor.name}</h3>
          <p>{selectedDoctor.specialization}</p>
          <div className="booking-row">
            <input type="date" value={selectedDate} onChange={(e) => setSelectedDate(e.target.value)} />
          </div>
          <div className="slot-list">
            {slots.length === 0 ? <div className="info-box">No slots available for this date.</div> : slots.map((slot) => (
              <button key={slot} type="button" className={selectedSlot === slot ? 'slot-button selected' : 'slot-button'} onClick={() => setSelectedSlot(slot)}>{slot.replace('T', ' ')}</button>
            ))}
          </div>
          <button className="primary-button" onClick={bookAppointment}>Book this appointment</button>
        </div>
      )}

      {bookingSummary && !bookingSummary.error && (
        <div className="booking-panel">
          <h3>Appointment booked</h3>
          <p>Appointment ID: {bookingSummary.id}</p>
          <p>Doctor: {bookingSummary.doctor_id}</p>
          <p>Time: {bookingSummary.start_time}</p>

          <div className="symptom-form">
            <h4>Patient symptom form</h4>
            <label>Chief complaint<input value={symptomForm.chief_complaint} onChange={(e) => setSymptomForm({ ...symptomForm, chief_complaint: e.target.value })} /></label>
            <label>Symptoms<textarea value={symptomForm.symptoms} onChange={(e) => setSymptomForm({ ...symptomForm, symptoms: e.target.value })} /></label>
            <label>Duration<input value={symptomForm.duration} onChange={(e) => setSymptomForm({ ...symptomForm, duration: e.target.value })} /></label>
            <label>Severity<select value={symptomForm.severity} onChange={(e) => setSymptomForm({ ...symptomForm, severity: e.target.value })}><option>Low</option><option>Medium</option><option>High</option></select></label>
            <label>Additional notes<textarea value={symptomForm.additional_notes} onChange={(e) => setSymptomForm({ ...symptomForm, additional_notes: e.target.value })} /></label>
            <button onClick={submitSymptoms}>Send symptoms for AI pre-visit summary</button>
          </div>
        </div>
      )}

      {summary && (
        <div className="booking-panel">
          <h3>AI-generated pre-visit summary</h3>
          <p className="muted">AI-generated administrative/clinical-support summary. It is not a diagnosis.</p>
          <p><strong>Urgency:</strong> {summary.detail?.urgency_level || 'Unavailable'}</p>
          <p><strong>Chief complaint:</strong> {summary.detail?.chief_complaint || 'Unavailable'}</p>
          <ul>
            {(summary.detail?.suggested_questions || []).map((question) => <li key={question}>{question}</li>)}
          </ul>
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
  const [doctorForm, setDoctorForm] = useState({ email: 'newdoctor@example.com', password: 'doctor123', full_name: 'Dr. Emma Brooks', specialization: 'Neurology', qualification: 'MD Neurology', experience_years: 7, slot_duration_minutes: 30 });
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

  useEffect(() => {
    api.get('/appointments').then((response) => setAppointments(response.data)).catch(() => setAppointments([])).finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="page-header"><div><p className="eyebrow">Appointments</p><h1>{roleLabels[auth?.user?.role] || 'Appointments'}</h1></div></div>
      {loading ? <div className="info-box">Loading appointments...</div> : appointments.length === 0 ? <div className="info-box">No appointments found.</div> : appointments.map((appointment) => (
        <div key={appointment.id} className="info-card">
          <h3>{appointment.doctor_id}</h3>
          <p>{appointment.start_time}</p>
          <p>Status: {appointment.status}</p>
        </div>
      ))}
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
