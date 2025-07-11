import React, { useState, useRef } from 'react'

const API_BASE_URL = 'http://localhost:8000'

// Toast notification component
const Toast = ({ message, type = 'success', onClose }) => {
  React.useEffect(() => {
    const timer = setTimeout(() => {
      onClose()
    }, 3000)
    return () => clearTimeout(timer)
  }, [onClose])

  return (
    <div className={`fixed top-4 left-1/2 transform -translate-x-1/2 z-50 px-6 py-3 rounded-lg shadow-lg font-semibold text-white transition-all duration-300 ${
      type === 'success' ? 'bg-green-500' : type === 'error' ? 'bg-red-500' : 'bg-blue-500'
    }`}>
      <div className="flex items-center space-x-2">
        <span>{message}</span>
        <button
          onClick={onClose}
          className="ml-2 text-white hover:text-gray-200 focus:outline-none"
        >
          ×
        </button>
      </div>
    </div>
  )
}

// Loading spinner component
const LoadingSpinner = () => (
  <div className="flex justify-center items-center py-8">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
  </div>
)

// Job card component
const JobCard = ({ job, onApply }) => {
  const maxTags = 3
  const displayTags = job.tags?.slice(0, maxTags) || []
  
  return (
    <div className="bg-white rounded-xl shadow-md p-6 mb-4 border border-gray-200">
      <div className="flex justify-between items-start mb-3">
        <div className="flex-1">
          <h3 className="text-lg font-bold text-gray-900 mb-1 line-clamp-2">
            {job.title}
          </h3>
          <p className="text-primary-600 font-semibold text-sm mb-1">
            {job.company}
          </p>
          <p className="text-gray-500 text-sm">
            📍 {job.location}
          </p>
        </div>
        <div className="ml-4">
          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
            {job.source}
          </span>
        </div>
      </div>
      
      {displayTags.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {displayTags.map((tag, index) => (
            <span 
              key={index}
              className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-primary-50 text-primary-700"
            >
              {tag}
            </span>
          ))}
          {job.tags?.length > maxTags && (
            <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-600">
              +{job.tags.length - maxTags} more
            </span>
          )}
        </div>
      )}
      
      <p className="text-gray-600 text-sm mb-6 line-clamp-3">
        {job.description || 'No description available'}
      </p>
      
      <div className="flex flex-col sm:flex-row gap-3">
        <button
          onClick={() => onApply(job)}
          className="flex-1 btn-primary text-center"
        >
          Apply Now
        </button>
        {job.apply_url && (
          <a
            href={job.apply_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 btn-secondary text-center"
          >
            View Details
          </a>
        )}
      </div>
    </div>
  )
}

// Main App component
const App = () => {
  const [currentScreen, setCurrentScreen] = useState('login') // 'login' | 'register' | 'jobs'
  const [userData, setUserData] = useState({
    id: null,
    name: '',
    email: '',
    linkedinUrl: '',
    githubUrl: '',
    skills: '',
    preferences: [],
    resume: null,
    loginCode: '',
    hasResume: false
  })
  const [loginData, setLoginData] = useState({
    name: '',
    loginCode: ''
  })
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(false)
  const [registering, setRegistering] = useState(false)
  const [toast, setToast] = useState(null)
  const [formErrors, setFormErrors] = useState({})
  const fileInputRef = useRef(null)

  const showToast = (message, type = 'success') => {
    setToast({ message, type })
  }

  const closeToast = () => {
    setToast(null)
  }

  const validateLoginForm = () => {
    const errors = {}
    
    if (!loginData.name.trim()) {
      errors.name = 'Name is required'
    }
    
    if (!loginData.loginCode.trim()) {
      errors.loginCode = 'Login code is required'
    } else if (!/^\d{4}$/.test(loginData.loginCode)) {
      errors.loginCode = 'Login code must be 4 digits'
    }
    
    setFormErrors(errors)
    return Object.keys(errors).length === 0
  }

  const validateForm = () => {
    const errors = {}
    
    if (!userData.name.trim()) {
      errors.name = 'Name is required'
    }
    
    if (!userData.email.trim()) {
      errors.email = 'Email is required'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(userData.email)) {
      errors.email = 'Please enter a valid email'
    }
    
    if (!userData.skills.trim()) {
      errors.skills = 'Skills are required'
    }
    
    if (userData.preferences.length === 0) {
      errors.preferences = 'Please select at least one preference'
    }
    
    setFormErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleLoginInputChange = (field, value) => {
    setLoginData(prev => ({
      ...prev,
      [field]: value
    }))
    
    // Clear error when user starts typing
    if (formErrors[field]) {
      setFormErrors(prev => ({
        ...prev,
        [field]: null
      }))
    }
  }

  const handleInputChange = (field, value) => {
    setUserData(prev => ({
      ...prev,
      [field]: value
    }))
    
    // Clear error when user starts typing
    if (formErrors[field]) {
      setFormErrors(prev => ({
        ...prev,
        [field]: null
      }))
    }
  }

  const handlePreferenceChange = (preference) => {
    setUserData(prev => ({
      ...prev,
      preferences: prev.preferences.includes(preference)
        ? prev.preferences.filter(p => p !== preference)
        : [...prev.preferences, preference]
    }))
    
    if (formErrors.preferences) {
      setFormErrors(prev => ({
        ...prev,
        preferences: null
      }))
    }
  }

  const handleResumeUpload = (event) => {
    const file = event.target.files[0]
    if (file) {
      const validTypes = ['application/pdf', 'text/plain', 'text/x-tex']
      if (!validTypes.includes(file.type)) {
        showToast('Please upload a PDF or TEX file', 'error')
        return
      }
      
      if (file.size > 5 * 1024 * 1024) { // 5MB limit
        showToast('File size must be less than 5MB', 'error')
        return
      }
      
      setUserData(prev => ({
        ...prev,
        resume: file
      }))
      showToast('Resume uploaded successfully!', 'success')
    }
  }

  const fetchJobs = async () => {
    setLoading(true)
    try {
      const [remoteokResponse, geminiResponse] = await Promise.allSettled([
        fetch(`${API_BASE_URL}/jobs/remoteok`),
        fetch(`${API_BASE_URL}/jobs/gemini`)
      ])
      
      let allJobs = []
      
      // Process RemoteOK response
      if (remoteokResponse.status === 'fulfilled' && remoteokResponse.value.ok) {
        const remoteokData = await remoteokResponse.value.json()
        allJobs = [...allJobs, ...remoteokData.jobs]
      }
      
      // Process Gemini response
      if (geminiResponse.status === 'fulfilled' && geminiResponse.value.ok) {
        const geminiData = await geminiResponse.value.json()
        allJobs = [...allJobs, ...geminiData.jobs]
      }
      
      if (allJobs.length === 0) {
        showToast('No jobs found. The API might be unavailable.', 'error')
      } else {
        setJobs(allJobs)
        showToast(`Found ${allJobs.length} jobs!`, 'success')
      }
    } catch (error) {
      console.error('Error fetching jobs:', error)
      showToast('Failed to fetch jobs. Please make sure the backend is running.', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleLogin = async (e) => {
    e.preventDefault()
    
    if (!validateLoginForm()) {
      showToast('Please fix the errors above', 'error')
      return
    }
    
    try {
      console.log('Attempting login with:', {
        name: loginData.name,
        login_code: loginData.loginCode
      })
      
      const response = await fetch(`${API_BASE_URL}/users/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: loginData.name,
          login_code: loginData.loginCode
        })
      })
      
      console.log('Login response status:', response.status, response.statusText)
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error('Login error response:', errorText)
        let errorMessage
        try {
          const error = JSON.parse(errorText)
          errorMessage = error.detail || 'Login failed'
        } catch {
          errorMessage = errorText || 'Login failed'
        }
        throw new Error(errorMessage)
      }
      
      const result = await response.json()
      console.log('Login result:', result)
      const user = result.user
      
      // Update user data from login response
      setUserData({
        id: user.id,
        name: user.name,
        email: user.email,
        linkedinUrl: user.linkedin_url,
        githubUrl: user.github_url,
        skills: user.skills,
        preferences: user.preferences,
        resume: null,
        loginCode: loginData.loginCode,
        hasResume: user.has_resume
      })
      
      showToast(`Welcome back, ${user.name}!`, 'success')
      setCurrentScreen('jobs')
      await fetchJobs()
      
    } catch (error) {
      console.error('Login error:', error)
      showToast(error.message || 'Login failed. Please check your credentials.', 'error')
    }
  }

  const handleFormSubmit = async (e) => {
    e.preventDefault()
    
    if (!validateForm()) {
      showToast('Please fix the errors above', 'error')
      return
    }
    
    setRegistering(true)
    
    try {
      // Create FormData for file upload
      const formData = new FormData()
      formData.append('name', userData.name)
      formData.append('email', userData.email)
      formData.append('linkedin_url', userData.linkedinUrl)
      formData.append('github_url', userData.githubUrl)
      formData.append('skills', userData.skills)
      formData.append('preferences', userData.preferences.join(','))
      
      if (userData.resume) {
        formData.append('resume', userData.resume)
      }
      
      console.log('Sending registration request with data:', {
        name: userData.name,
        email: userData.email,
        linkedin_url: userData.linkedinUrl,
        github_url: userData.githubUrl,
        skills: userData.skills,
        preferences: userData.preferences.join(','),
        hasResume: !!userData.resume
      })
      
      const response = await fetch(`${API_BASE_URL}/users/register`, {
        method: 'POST',
        body: formData
      })
      
      console.log('Response status:', response.status, response.statusText)
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error('Error response:', errorText)
        let errorMessage
        try {
          const error = JSON.parse(errorText)
          errorMessage = error.detail || 'Registration failed'
        } catch {
          errorMessage = errorText || 'Registration failed'
        }
        throw new Error(errorMessage)
      }
      
      const result = await response.json()
      console.log('Registration result:', result)
      
      // Update user data with login code
      setUserData(prev => ({
        ...prev,
        id: result.user_id,
        loginCode: result.login_code
      }))
      
      // Show success message with login code
      showToast(
        `Registration successful! Your login code is: ${result.login_code}`, 
        'success'
      )
      
      // Pre-fill the name in login form
      setLoginData(prev => ({
        ...prev,
        name: userData.name
      }))
      
      // Don't automatically switch to login, let user see the code and click to continue
      
    } catch (error) {
      console.error('Registration error:', error)
      console.error('Error details:', {
        message: error.message,
        name: error.name,
        stack: error.stack
      })
      showToast(error.message || 'Registration failed. Please try again.', 'error')
    } finally {
      setRegistering(false)
    }
  }

  const handleApply = async (job) => {
    try {
      // Record job application in backend
      const applicationData = {
        user_id: userData.id,
        user_email: userData.email,
        job_title: job.title,
        company: job.company,
        job_source: job.source,
        job_url: job.apply_url || ""
      }
      
      const response = await fetch(`${API_BASE_URL}/users/apply`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(applicationData)
      })
      
      if (!response.ok) {
        throw new Error('Failed to record application')
      }
      
      showToast('Resume Generated and Application Sent!', 'success')
      console.log('Applied to:', job.title, 'at', job.company)
      console.log('User data:', userData)
    } catch (error) {
      console.error('Error recording application:', error)
      showToast('Application sent but not recorded. Please try again.', 'error')
    }
  }

  const handleBackToForm = () => {
    setCurrentScreen('login')
    setJobs([])
    // Clear sensitive data including login code when logging out
    setLoginData({ name: '', loginCode: '' })
    setUserData(prev => ({
      ...prev,
      id: null,
      loginCode: '',
      hasResume: false
    }))
  }

  const switchToRegister = () => {
    setCurrentScreen('register')
    setFormErrors({})
    // Clear login code when explicitly switching to register
    setUserData(prev => ({...prev, loginCode: ''}))
    setLoginData({ name: '', loginCode: '' })
  }

  const switchToLogin = () => {
    setCurrentScreen('login')
    setFormErrors({})
    // Don't clear login code when switching from registration
    // Only clear it when explicitly logging out
  }

  const preferenceOptions = [
    { id: 'frontend', label: 'Frontend Development', icon: '🎨' },
    { id: 'backend', label: 'Backend Development', icon: '⚙️' },
    { id: 'fullstack', label: 'Full Stack Development', icon: '🚀' },
    { id: 'mobile', label: 'Mobile Development', icon: '📱' },
    { id: 'ai', label: 'AI/Machine Learning', icon: '🤖' },
    { id: 'data', label: 'Data Science', icon: '📊' },
    { id: 'devops', label: 'DevOps', icon: '🔧' },
    { id: 'design', label: 'UI/UX Design', icon: '✨' }
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Toast notifications */}
      {toast && (
        <Toast 
          message={toast.message} 
          type={toast.type} 
          onClose={closeToast} 
        />
      )}

      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-md mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">
              SwipingForJobs
            </h1>
            {currentScreen === 'jobs' && (
              <button
                onClick={handleBackToForm}
                className="text-primary-600 hover:text-primary-700 font-medium text-sm"
              >
                ← Logout
              </button>
            )}
            {currentScreen === 'register' && (
              <button
                onClick={switchToLogin}
                className="text-primary-600 hover:text-primary-700 font-medium text-sm"
              >
                ← Back to Login
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-md mx-auto px-4 py-6">
        {currentScreen === 'login' ? (
          /* Login Form */
          <div className="bg-white rounded-xl shadow-md p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-6">
              Welcome Back
            </h2>
            
            <form onSubmit={handleLogin} className="space-y-6">
              {/* Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Your Name *
                </label>
                <input
                  type="text"
                  value={loginData.name}
                  onChange={(e) => handleLoginInputChange('name', e.target.value)}
                  className={`w-full px-4 py-3 border rounded-lg focus-ring ${
                    formErrors.name ? 'border-red-300' : 'border-gray-300'
                  }`}
                  placeholder="Enter your name"
                />
                {formErrors.name && (
                  <p className="mt-1 text-sm text-red-600">{formErrors.name}</p>
                )}
              </div>

              {/* Login Code */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  4-Digit Login Code *
                </label>
                <input
                  type="text"
                  value={loginData.loginCode}
                  onChange={(e) => handleLoginInputChange('loginCode', e.target.value.replace(/\D/g, '').slice(0, 4))}
                  className={`w-full px-4 py-3 border rounded-lg focus-ring text-center text-2xl tracking-widest ${
                    formErrors.loginCode ? 'border-red-300' : 'border-gray-300'
                  }`}
                  placeholder="0000"
                  maxLength="4"
                />
                {formErrors.loginCode && (
                  <p className="mt-1 text-sm text-red-600">{formErrors.loginCode}</p>
                )}
                <p className="mt-1 text-xs text-gray-500">
                  Enter the 4-digit code you received during registration
                </p>
              </div>

              {/* Login Button */}
              <button
                type="submit"
                className="w-full btn-primary"
              >
                Login
              </button>
            </form>

            {/* Register Link */}
            <div className="mt-6 text-center">
              <p className="text-gray-600">
                Don't have an account?{' '}
                <button
                  onClick={switchToRegister}
                  className="text-primary-600 hover:text-primary-700 font-medium"
                >
                  Register here
                </button>
              </p>
            </div>
          </div>
        ) : currentScreen === 'register' ? (
          /* Registration Form */
          <div className="bg-white rounded-xl shadow-md p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-6">
              Create Your Profile
            </h2>
            
            <form onSubmit={handleFormSubmit} className="space-y-6">
              {/* Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Full Name *
                </label>
                <input
                  type="text"
                  value={userData.name}
                  onChange={(e) => handleInputChange('name', e.target.value)}
                  className={`w-full px-4 py-3 border rounded-lg focus-ring ${
                    formErrors.name ? 'border-red-300' : 'border-gray-300'
                  }`}
                  placeholder="Enter your full name"
                />
                {formErrors.name && (
                  <p className="mt-1 text-sm text-red-600">{formErrors.name}</p>
                )}
              </div>

              {/* Email */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email Address *
                </label>
                <input
                  type="email"
                  value={userData.email}
                  onChange={(e) => handleInputChange('email', e.target.value)}
                  className={`w-full px-4 py-3 border rounded-lg focus-ring ${
                    formErrors.email ? 'border-red-300' : 'border-gray-300'
                  }`}
                  placeholder="Enter your email"
                />
                {formErrors.email && (
                  <p className="mt-1 text-sm text-red-600">{formErrors.email}</p>
                )}
              </div>

              {/* LinkedIn URL */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  LinkedIn URL
                </label>
                <input
                  type="url"
                  value={userData.linkedinUrl}
                  onChange={(e) => handleInputChange('linkedinUrl', e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus-ring"
                  placeholder="https://linkedin.com/in/yourname"
                />
              </div>

              {/* GitHub URL */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  GitHub URL
                </label>
                <input
                  type="url"
                  value={userData.githubUrl}
                  onChange={(e) => handleInputChange('githubUrl', e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus-ring"
                  placeholder="https://github.com/yourusername"
                />
              </div>

              {/* Skills */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Skills *
                </label>
                <input
                  type="text"
                  value={userData.skills}
                  onChange={(e) => handleInputChange('skills', e.target.value)}
                  className={`w-full px-4 py-3 border rounded-lg focus-ring ${
                    formErrors.skills ? 'border-red-300' : 'border-gray-300'
                  }`}
                  placeholder="React, Node.js, Python, etc. (comma-separated)"
                />
                {formErrors.skills && (
                  <p className="mt-1 text-sm text-red-600">{formErrors.skills}</p>
                )}
              </div>

              {/* Preferences */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Job Preferences *
                </label>
                <div className="grid grid-cols-2 gap-3">
                  {preferenceOptions.map((option) => (
                    <button
                      key={option.id}
                      type="button"
                      onClick={() => handlePreferenceChange(option.id)}
                      className={`p-3 rounded-lg border text-left transition-colors ${
                        userData.preferences.includes(option.id)
                          ? 'border-primary-500 bg-primary-50 text-primary-700'
                          : 'border-gray-300 hover:border-gray-400'
                      }`}
                    >
                      <div className="flex items-center space-x-2">
                        <span className="text-lg">{option.icon}</span>
                        <span className="text-sm font-medium">{option.label}</span>
                      </div>
                    </button>
                  ))}
                </div>
                {formErrors.preferences && (
                  <p className="mt-1 text-sm text-red-600">{formErrors.preferences}</p>
                )}
              </div>

              {/* Resume Upload */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Resume Upload
                </label>
                <div className="flex items-center space-x-4">
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleResumeUpload}
                    accept=".pdf,.tex,.txt"
                    className="hidden"
                  />
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="btn-secondary"
                  >
                    Choose File
                  </button>
                  {userData.resume && (
                    <span className="text-sm text-gray-600">
                      {userData.resume.name}
                    </span>
                  )}
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  Upload your resume in PDF or TEX format (max 5MB)
                </p>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                className="w-full btn-primary"
                disabled={registering}
              >
                {registering ? 'Creating Account...' : 'Create Account'}
              </button>
            </form>

            {/* Show login code if user just registered */}
            {userData.loginCode && (
              <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
                <h3 className="text-lg font-semibold text-green-800 mb-2">
                  🎉 Registration Successful!
                </h3>
                <p className="text-green-700 mb-3">
                  Your 4-digit login code is:
                </p>
                <div className="text-center">
                  <span className="inline-block px-6 py-3 bg-green-100 border-2 border-green-300 rounded-lg text-3xl font-bold text-green-800 tracking-widest">
                    {userData.loginCode}
                  </span>
                </div>
                <p className="text-green-600 text-sm mt-3 text-center mb-4">
                  Save this code! You'll need it to login with your name.
                </p>
                <button
                  onClick={() => {
                    // Pre-fill both name and code for convenience
                    setLoginData({
                      name: userData.name,
                      loginCode: userData.loginCode
                    })
                    setCurrentScreen('login')
                    showToast('Name and code have been filled in for you!', 'info')
                  }}
                  className="w-full btn-primary"
                >
                  Continue to Login
                </button>
              </div>
            )}

            {/* Login Link */}
            <div className="mt-6 text-center">
              <p className="text-gray-600">
                Already have an account?{' '}
                <button
                  onClick={switchToLogin}
                  className="text-primary-600 hover:text-primary-700 font-medium"
                >
                  Login here
                </button>
              </p>
            </div>
          </div>
        ) : (
          /* Jobs Feed */
          <div>
            <div className="mb-6">
              <h2 className="text-xl font-bold text-gray-900 mb-2">
                Jobs for {userData.name}
              </h2>
              <p className="text-gray-600 text-sm">
                {jobs.length} opportunities found
              </p>
            </div>

            {loading ? (
              <LoadingSpinner />
            ) : jobs.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-gray-500 text-lg mb-4">No jobs found</p>
                <p className="text-gray-400 text-sm mb-6">
                  Make sure your backend server is running on port 8000
                </p>
                <button
                  onClick={fetchJobs}
                  className="btn-primary"
                >
                  Try Again
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {jobs.map((job, index) => (
                  <JobCard
                    key={`${job.source}-${index}`}
                    job={job}
                    onApply={handleApply}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}

export default App
