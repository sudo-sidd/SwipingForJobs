import React, { useState, useEffect } from 'react'
import sessionManager from './sessionManager'
import GitHubIntegration from './GitHubIntegration'

const API_BASE_URL = 'http://localhost:8000'

const Profile = ({ userData, onBack, onUpdate }) => {
  console.log('Profile received userData:', userData)
  
  const [profileData, setProfileData] = useState({
    name: userData.name || '',
    email: userData.email || '',
    linkedin_url: userData.linkedinUrl || '',
    github_url: userData.githubUrl || '',
    portfolio_url: userData.portfolioUrl || '',
    phone_number: userData.phoneNumber || '',
    location: userData.location || '',
    bio: userData.bio || '',
    skills: userData.skills || '',
    preferences: userData.preferences || [],
    work_mode: userData.workMode || 'remote',
    experience_level: userData.experienceLevel || 'entry',
    salary_min: userData.salaryMin || '',
    salary_max: userData.salaryMax || '',
    currency: userData.currency || 'USD',
    resume_filename: userData.resume_filename || userData.resumeFilename || '',
    linkedin_data: userData.linkedinData || '',
    github_data: userData.githubData || '',
    resume_processed_data: userData.resumeProcessedData || ''
  })
  
  const [editing, setEditing] = useState(false)
  const [loading, setLoading] = useState(false)
  const [processingResume, setProcessingResume] = useState(false)
  const [applications, setApplications] = useState([])
  const [projects, setProjects] = useState([])
  const [activeTab, setActiveTab] = useState('overview')
  const [resumeData, setResumeData] = useState(null)

  useEffect(() => {
    fetchApplications()
    fetchProjects()
    // Parse resume data if available
    if (userData.resumeProcessedData) {
      try {
        const parsed = JSON.parse(userData.resumeProcessedData)
        setResumeData(parsed)
        console.log('Parsed resume data:', parsed)
      } catch (error) {
        console.error('Error parsing resume data:', error)
      }
    }
  }, [userData.resumeProcessedData])

  const fetchApplications = async () => {
    try {
      if (!sessionManager.isLoggedIn()) {
        console.error('Not authenticated')
        return
      }
      
      const response = await fetch(`${API_BASE_URL}/users/applications/${userData.id}`, {
        headers: sessionManager.getAuthHeaders()
      })
      
      if (response.status === 401) {
        console.error('Session expired')
        return
      }
      
      if (response.ok) {
        const data = await response.json()
        setApplications(data.applications)
      }
    } catch (error) {
      console.error('Error fetching applications:', error)
    }
  }

  const fetchProjects = async () => {
    try {
      if (!sessionManager.isLoggedIn()) {
        console.error('Not authenticated')
        return
      }
      
      const response = await fetch(`${API_BASE_URL}/users/projects/${userData.id}`, {
        headers: sessionManager.getAuthHeaders()
      })
      
      if (response.status === 401) {
        console.error('Session expired')
        return
      }
      
      if (response.ok) {
        const data = await response.json()
        setProjects(data.projects)
      }
    } catch (error) {
      console.error('Error fetching projects:', error)
    }
  }

  const handleInputChange = (field, value) => {
    setProfileData(prev => ({
      ...prev,
      [field]: value
    }))
  }

  const handlePreferenceChange = (preference) => {
    setProfileData(prev => ({
      ...prev,
      preferences: prev.preferences.includes(preference)
        ? prev.preferences.filter(p => p !== preference)
        : [...prev.preferences, preference]
    }))
  }

  const handleSave = async () => {
    setLoading(true)
    try {
      const updateData = {
        linkedin_url: profileData.linkedin_url,
        github_url: profileData.github_url,
        portfolio_url: profileData.portfolio_url,
        phone_number: profileData.phone_number,
        location: profileData.location,
        bio: profileData.bio,
        work_mode: profileData.work_mode,
        experience_level: profileData.experience_level,
        salary_min: profileData.salary_min ? parseInt(profileData.salary_min) : null,
        salary_max: profileData.salary_max ? parseInt(profileData.salary_max) : null,
        currency: profileData.currency,
        skills: profileData.skills,
        preferences: profileData.preferences
      }

      const response = await fetch(`${API_BASE_URL}/users/profile/${userData.id}`, {
        method: 'PUT',
        headers: {
          ...sessionManager.getAuthHeaders()
        },
        body: JSON.stringify(updateData)
      })

      if (response.status === 401) {
        alert('Session expired. Please log in again.')
        return
      }

      if (response.ok) {
        const result = await response.json()
        onUpdate(result.user) // Update parent component with new data
        sessionManager.updateUser(result.user) // Update session storage
        setEditing(false)
      } else {
        throw new Error('Failed to update profile')
      }
    } catch (error) {
      console.error('Error updating profile:', error)
      alert('Failed to update profile. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleProcessResume = async () => {
    setProcessingResume(true)
    try {
      const response = await fetch(`${API_BASE_URL}/users/process-resume/${userData.id}`, {
        method: 'POST',
        headers: sessionManager.getAuthHeaders()
      })

      if (response.status === 401) {
        alert('Session expired. Please log in again.')
        return
      }

      if (response.ok) {
        const result = await response.json()
        setResumeData(result.processed_data)
        onUpdate(result.user) // Update parent component with new data
        sessionManager.updateUser(result.user) // Update session storage
        fetchProjects() // Refresh projects after processing
        alert('Resume processed successfully! Check your profile for extracted information.')
      } else {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to process resume')
      }
    } catch (error) {
      console.error('Error processing resume:', error)
      alert('Failed to process resume: ' + error.message)
    } finally {
      setProcessingResume(false)
    }
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

  const workModeOptions = [
    { value: 'remote', label: 'Remote Only', icon: '🏠' },
    { value: 'hybrid', label: 'Hybrid', icon: '🔄' },
    { value: 'onsite', label: 'On-site', icon: '🏢' }
  ]

  const experienceLevels = [
    { value: 'entry', label: 'Entry Level', icon: '🌱' },
    { value: 'junior', label: 'Junior (0-2 years)', icon: '📝' },
    { value: 'mid', label: 'Mid Level (2-5 years)', icon: '⚡' },
    { value: 'senior', label: 'Senior (5+ years)', icon: '🏆' }
  ]

  const currencies = ['USD', 'EUR', 'GBP', 'INR', 'CAD', 'AUD', 'JPY']

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4">
          <button
            onClick={onBack}
            className="text-primary-600 hover:text-primary-700 font-medium text-sm"
          >
            ← Back to Jobs
          </button>
          <h1 className="text-2xl font-bold text-gray-900">My Profile</h1>
        </div>
        {!editing && (
          <button
            onClick={() => setEditing(true)}
            className="btn-primary"
          >
            Edit Profile
          </button>
        )}
      </div>

      {/* Tab Navigation */}
      <div className="flex space-x-1 mb-6 bg-gray-100 p-1 rounded-lg">
        {['overview', 'preferences', 'projects', 'github', 'applications'].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 py-2 px-4 text-sm font-medium rounded-md transition-colors ${
              activeTab === tab
                ? 'bg-white text-primary-600 shadow-sm'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            {tab === 'overview' && '👤 Overview'}
            {tab === 'preferences' && '⚙️ Preferences'}
            {tab === 'projects' && '🚀 Projects'}
            {tab === 'github' && '💻 GitHub'}
            {tab === 'applications' && '📋 Applications'}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Basic Information */}
          <div className="bg-white rounded-xl shadow-md p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Basic Information</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Name</label>
                <input
                  type="text"
                  value={profileData.name}
                  disabled={!editing}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
                <input
                  type="email"
                  value={profileData.email}
                  disabled={!editing}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Phone Number</label>
                <input
                  type="tel"
                  value={profileData.phone_number}
                  onChange={(e) => handleInputChange('phone_number', e.target.value)}
                  disabled={!editing}
                  className={`w-full px-3 py-2 border border-gray-300 rounded-lg ${editing ? 'focus-ring' : 'bg-gray-50'}`}
                  placeholder="Your phone number"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Location</label>
                <input
                  type="text"
                  value={profileData.location}
                  onChange={(e) => handleInputChange('location', e.target.value)}
                  disabled={!editing}
                  className={`w-full px-3 py-2 border border-gray-300 rounded-lg ${editing ? 'focus-ring' : 'bg-gray-50'}`}
                  placeholder="City, Country"
                />
              </div>
            </div>
          </div>

          {/* Bio */}
          <div className="bg-white rounded-xl shadow-md p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">About Me</h2>
            <textarea
              value={profileData.bio}
              onChange={(e) => handleInputChange('bio', e.target.value)}
              disabled={!editing}
              rows={4}
              className={`w-full px-3 py-2 border border-gray-300 rounded-lg ${editing ? 'focus-ring' : 'bg-gray-50'}`}
              placeholder="Tell us about yourself, your background, and what you're looking for..."
            />
          </div>

          {/* Links */}
          <div className="bg-white rounded-xl shadow-md p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Professional Links</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">LinkedIn URL</label>
                <input
                  type="url"
                  value={profileData.linkedin_url}
                  onChange={(e) => handleInputChange('linkedin_url', e.target.value)}
                  disabled={!editing}
                  className={`w-full px-3 py-2 border border-gray-300 rounded-lg ${editing ? 'focus-ring' : 'bg-gray-50'}`}
                  placeholder="https://linkedin.com/in/yourname"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">GitHub URL</label>
                <input
                  type="url"
                  value={profileData.github_url}
                  onChange={(e) => handleInputChange('github_url', e.target.value)}
                  disabled={!editing}
                  className={`w-full px-3 py-2 border border-gray-300 rounded-lg ${editing ? 'focus-ring' : 'bg-gray-50'}`}
                  placeholder="https://github.com/yourusername"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Portfolio URL</label>
                <input
                  type="url"
                  value={profileData.portfolio_url}
                  onChange={(e) => handleInputChange('portfolio_url', e.target.value)}
                  disabled={!editing}
                  className={`w-full px-3 py-2 border border-gray-300 rounded-lg ${editing ? 'focus-ring' : 'bg-gray-50'}`}
                  placeholder="https://yourportfolio.com"
                />
              </div>
            </div>
          </div>

          {/* Skills */}
          <div className="bg-white rounded-xl shadow-md p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Skills</h2>
            <textarea
              value={profileData.skills}
              onChange={(e) => handleInputChange('skills', e.target.value)}
              disabled={!editing}
              rows={3}
              className={`w-full px-3 py-2 border border-gray-300 rounded-lg ${editing ? 'focus-ring' : 'bg-gray-50'}`}
              placeholder="React, Node.js, Python, Docker, etc. (comma-separated)"
            />
          </div>

          {/* Resume */}
          <div className="bg-white rounded-xl shadow-md p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Resume</h2>
              {profileData.resume_filename && (
                <button
                  onClick={handleProcessResume}
                  disabled={processingResume}
                  className="btn-secondary text-sm"
                >
                  {processingResume ? 'Processing...' : 'Extract Info with AI'}
                </button>
              )}
            </div>
            
            {profileData.resume_filename ? (
              <div className="space-y-4">
                <div className="flex items-center space-x-3">
                  <div className="flex-1">
                    <p className="text-sm text-gray-600">Uploaded file:</p>
                    <p className="font-medium text-gray-900">{profileData.resume_filename}</p>
                  </div>
                  <button className="btn-secondary text-sm">Download</button>
                </div>
                
                {/* Display extracted resume data */}
                {resumeData && (
                  <div className="mt-6 border-t pt-4">
                    <h3 className="text-md font-semibold text-gray-900 mb-3">Extracted Information</h3>
                    
                    {/* Basic Info from Resume */}
                    {(resumeData.name || resumeData.email || resumeData.phone || resumeData.location) && (
                      <div className="mb-4">
                        <h4 className="text-sm font-medium text-gray-700 mb-2">Contact Information</h4>
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          {resumeData.name && <p><span className="font-medium">Name:</span> {resumeData.name}</p>}
                          {resumeData.email && <p><span className="font-medium">Email:</span> {resumeData.email}</p>}
                          {resumeData.phone && <p><span className="font-medium">Phone:</span> {resumeData.phone}</p>}
                          {resumeData.location && <p><span className="font-medium">Location:</span> {resumeData.location}</p>}
                        </div>
                      </div>
                    )}
                    
                    {/* Links from Resume */}
                    {(resumeData.linkedin || resumeData.github || resumeData.portfolio) && (
                      <div className="mb-4">
                        <h4 className="text-sm font-medium text-gray-700 mb-2">Professional Links</h4>
                        <div className="space-y-1 text-sm">
                          {resumeData.linkedin && (
                            <p><span className="font-medium">LinkedIn:</span> <a href={resumeData.linkedin} target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline">{resumeData.linkedin}</a></p>
                          )}
                          {resumeData.github && (
                            <p><span className="font-medium">GitHub:</span> <a href={resumeData.github} target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline">{resumeData.github}</a></p>
                          )}
                          {resumeData.portfolio && (
                            <p><span className="font-medium">Portfolio:</span> <a href={resumeData.portfolio} target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline">{resumeData.portfolio}</a></p>
                          )}
                        </div>
                      </div>
                    )}
                    
                    {/* Summary */}
                    {resumeData.summary && (
                      <div className="mb-4">
                        <h4 className="text-sm font-medium text-gray-700 mb-2">Professional Summary</h4>
                        <p className="text-sm text-gray-600">{resumeData.summary}</p>
                      </div>
                    )}
                    
                    {/* Skills */}
                    {resumeData.skills && resumeData.skills.length > 0 && (
                      <div className="mb-4">
                        <h4 className="text-sm font-medium text-gray-700 mb-2">Skills from Resume</h4>
                        <div className="flex flex-wrap gap-2">
                          {resumeData.skills.map((skill, index) => (
                            <span key={index} className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-blue-50 text-blue-700">
                              {skill}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {/* Experience */}
                    {resumeData.experience && resumeData.experience.length > 0 && (
                      <div className="mb-4">
                        <h4 className="text-sm font-medium text-gray-700 mb-2">Experience</h4>
                        <div className="space-y-2">
                          {resumeData.experience.slice(0, 3).map((exp, index) => (
                            <div key={index} className="text-sm">
                              <p className="font-medium">{exp.title} at {exp.company}</p>
                              <p className="text-gray-600 text-xs">{exp.duration}</p>
                              {exp.description && <p className="text-gray-600 text-xs mt-1">{exp.description}</p>}
                            </div>
                          ))}
                          {resumeData.experience.length > 3 && (
                            <p className="text-xs text-gray-500">+{resumeData.experience.length - 3} more experiences</p>
                          )}
                        </div>
                      </div>
                    )}
                    
                    {/* Education */}
                    {resumeData.education && resumeData.education.length > 0 && (
                      <div className="mb-4">
                        <h4 className="text-sm font-medium text-gray-700 mb-2">Education</h4>
                        <div className="space-y-1">
                          {resumeData.education.map((edu, index) => (
                            <div key={index} className="text-sm">
                              <p className="font-medium">{edu.degree}</p>
                              <p className="text-gray-600 text-xs">{edu.institution} - {edu.year}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {/* Projects */}
                    {resumeData.projects && resumeData.projects.length > 0 && (
                      <div className="mb-4">
                        <h4 className="text-sm font-medium text-gray-700 mb-2">Projects</h4>
                        <div className="space-y-2">
                          {resumeData.projects.slice(0, 2).map((project, index) => (
                            <div key={index} className="text-sm">
                              <p className="font-medium">{project.name}</p>
                              <p className="text-gray-600 text-xs">{project.description}</p>
                              {project.technologies && project.technologies.length > 0 && (
                                <div className="flex flex-wrap gap-1 mt-1">
                                  {project.technologies.map((tech, techIndex) => (
                                    <span key={techIndex} className="inline-flex items-center px-1 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">
                                      {tech}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                          ))}
                          {resumeData.projects.length > 2 && (
                            <p className="text-xs text-gray-500">+{resumeData.projects.length - 2} more projects</p>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <p className="text-gray-500 text-sm">No resume uploaded</p>
            )}
          </div>
        </div>
      )}

      {activeTab === 'preferences' && (
        <div className="space-y-6">
          {/* Job Preferences */}
          <div className="bg-white rounded-xl shadow-md p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Job Type Preferences</h2>
            <div className="grid grid-cols-2 gap-3">
              {preferenceOptions.map((option) => (
                <button
                  key={option.id}
                  type="button"
                  onClick={() => editing && handlePreferenceChange(option.id)}
                  disabled={!editing}
                  className={`p-3 rounded-lg border text-left transition-colors ${
                    profileData.preferences.includes(option.id)
                      ? 'border-primary-500 bg-primary-50 text-primary-700'
                      : 'border-gray-300 hover:border-gray-400'
                  } ${!editing ? 'opacity-75' : ''}`}
                >
                  <div className="flex items-center space-x-2">
                    <span className="text-lg">{option.icon}</span>
                    <span className="text-sm font-medium">{option.label}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Work Mode */}
          <div className="bg-white rounded-xl shadow-md p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Work Mode</h2>
            <div className="grid grid-cols-3 gap-3">
              {workModeOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => editing && handleInputChange('work_mode', option.value)}
                  disabled={!editing}
                  className={`p-3 rounded-lg border text-center transition-colors ${
                    profileData.work_mode === option.value
                      ? 'border-primary-500 bg-primary-50 text-primary-700'
                      : 'border-gray-300 hover:border-gray-400'
                  } ${!editing ? 'opacity-75' : ''}`}
                >
                  <div className="text-2xl mb-1">{option.icon}</div>
                  <div className="text-sm font-medium">{option.label}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Experience Level */}
          <div className="bg-white rounded-xl shadow-md p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Experience Level</h2>
            <div className="grid grid-cols-2 gap-3">
              {experienceLevels.map((level) => (
                <button
                  key={level.value}
                  onClick={() => editing && handleInputChange('experience_level', level.value)}
                  disabled={!editing}
                  className={`p-3 rounded-lg border text-left transition-colors ${
                    profileData.experience_level === level.value
                      ? 'border-primary-500 bg-primary-50 text-primary-700'
                      : 'border-gray-300 hover:border-gray-400'
                  } ${!editing ? 'opacity-75' : ''}`}
                >
                  <div className="flex items-center space-x-2">
                    <span className="text-lg">{level.icon}</span>
                    <span className="text-sm font-medium">{level.label}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Salary Expectations */}
          <div className="bg-white rounded-xl shadow-md p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Salary Expectations</h2>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Minimum</label>
                <input
                  type="number"
                  value={profileData.salary_min}
                  onChange={(e) => handleInputChange('salary_min', e.target.value)}
                  disabled={!editing}
                  className={`w-full px-3 py-2 border border-gray-300 rounded-lg ${editing ? 'focus-ring' : 'bg-gray-50'}`}
                  placeholder="50000"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Maximum</label>
                <input
                  type="number"
                  value={profileData.salary_max}
                  onChange={(e) => handleInputChange('salary_max', e.target.value)}
                  disabled={!editing}
                  className={`w-full px-3 py-2 border border-gray-300 rounded-lg ${editing ? 'focus-ring' : 'bg-gray-50'}`}
                  placeholder="80000"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Currency</label>
                <select
                  value={profileData.currency}
                  onChange={(e) => handleInputChange('currency', e.target.value)}
                  disabled={!editing}
                  className={`w-full px-3 py-2 border border-gray-300 rounded-lg ${editing ? 'focus-ring' : 'bg-gray-50'}`}
                >
                  {currencies.map(currency => (
                    <option key={currency} value={currency}>{currency}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'projects' && (
        <div className="bg-white rounded-xl shadow-md p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Projects ({projects.length + (resumeData?.projects?.length || 0)})
          </h2>
          {/* Resume-extracted projects */}
          {resumeData?.projects?.length > 0 && (
            <div className="mb-8">
              <h3 className="text-md font-semibold text-gray-900 mb-2">Projects from Resume ({resumeData.projects.length})</h3>
              <div className="space-y-6">
                {resumeData.projects.map((project, index) => (
                  <div key={index} className="border border-blue-100 rounded-lg p-6 bg-blue-50">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <h4 className="text-lg font-semibold text-blue-900">{project.name}</h4>
                        {project.description && (
                          <p className="text-sm text-blue-700 mt-1">{project.description}</p>
                        )}
                      </div>
                    </div>
                    {project.technologies && project.technologies.length > 0 && (
                      <div className="mb-2">
                        <h4 className="text-sm font-medium text-blue-700 mb-1">Technologies</h4>
                        <div className="flex flex-wrap gap-2">
                          {project.technologies.map((tech, techIndex) => (
                            <span key={techIndex} className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-blue-100 text-blue-700">
                              {tech}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    <div className="flex flex-wrap gap-4 text-sm text-blue-700">
                      {project.start_date && (
                        <span>Started: {project.start_date}</span>
                      )}
                      {project.end_date && (
                        <span>Ended: {project.end_date}</span>
                      )}
                      {project.is_current && (
                        <span className="text-green-600 font-medium">Current</span>
                      )}
                    </div>
                    <div className="flex space-x-4 mt-2">
                      {project.url && (
                        <a
                          href={project.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center text-sm text-primary-600 hover:text-primary-700"
                        >
                          🔗 View Project
                        </a>
                      )}
                      {project.github && (
                        <a
                          href={project.github}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center text-sm text-primary-600 hover:text-primary-700"
                        >
                          📄 GitHub
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {/* DB projects */}
          {projects.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-500">No database projects yet</p>
              <p className="text-sm text-gray-400 mt-1">Process your resume to extract projects or add them manually</p>
            </div>
          ) : (
            <div className="space-y-6">
              {projects.map((project, index) => (
                <div key={index} className="border border-gray-200 rounded-lg p-6">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">{project.project_name}</h3>
                      {project.description && (
                        <p className="text-sm text-gray-600 mt-1">{project.description}</p>
                      )}
                    </div>
                    {project.featured && (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                        Featured
                      </span>
                    )}
                  </div>
                  {project.technologies && project.technologies.length > 0 && (
                    <div className="mb-4">
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Technologies</h4>
                      <div className="flex flex-wrap gap-2">
                        {project.technologies.map((tech, techIndex) => (
                          <span key={techIndex} className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-blue-50 text-blue-700">
                            {tech}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  <div className="flex flex-wrap gap-4 text-sm text-gray-500">
                    {project.start_date && (
                      <span>Started: {new Date(project.start_date).toLocaleDateString()}</span>
                    )}
                    {project.end_date && (
                      <span>Ended: {new Date(project.end_date).toLocaleDateString()}</span>
                    )}
                    {project.is_current && (
                      <span className="text-green-600 font-medium">Current</span>
                    )}
                  </div>
                  <div className="flex space-x-4 mt-4">
                    {project.project_url && (
                      <a
                        href={project.project_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center text-sm text-primary-600 hover:text-primary-700"
                      >
                        🔗 View Project
                      </a>
                    )}
                    {project.github_url && (
                      <a
                        href={project.github_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center text-sm text-primary-600 hover:text-primary-700"
                      >
                        📄 GitHub
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'github' && (
        <div className="bg-white rounded-xl shadow-md p-6">
          <GitHubIntegration userId={userData.id} />
        </div>
      )}

      {activeTab === 'applications' && (
        <div className="bg-white rounded-xl shadow-md p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Job Applications ({applications.length})
          </h2>
          {applications.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-500">No applications yet</p>
              <p className="text-sm text-gray-400 mt-1">Start applying to jobs to see them here</p>
            </div>
          ) : (
            <div className="space-y-4">
              {applications.map((app, index) => (
                <div key={index} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="font-semibold text-gray-900">{app.job_title}</h3>
                      <p className="text-sm text-gray-600">{app.company}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        Applied on {new Date(app.applied_at).toLocaleDateString()}
                      </p>
                    </div>
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {app.job_source}
                    </span>
                  </div>
                  {app.job_url && (
                    <a
                      href={app.job_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center mt-2 text-sm text-primary-600 hover:text-primary-700"
                    >
                      View Job →
                    </a>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Save/Cancel Buttons */}
      {editing && (
        <div className="flex justify-end space-x-4 mt-6">
          <button
            onClick={() => setEditing(false)}
            className="btn-secondary"
            disabled={loading}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="btn-primary"
            disabled={loading}
          >
            {loading ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      )}
    </div>
  )
}

export default Profile
