import React, { useState, useEffect } from 'react'

const ApiTest = () => {
  const [status, setStatus] = useState('testing')
  const [results, setResults] = useState({})

  useEffect(() => {
    const testApi = async () => {
      const tests = [
        { name: 'Backend Root', url: 'http://localhost:8000/' },
        { name: 'RemoteOK Jobs', url: 'http://localhost:8000/jobs/remoteok' },
        { name: 'Gemini Jobs', url: 'http://localhost:8000/jobs/gemini' }
      ]

      const testResults = {}
      
      for (const test of tests) {
        try {
          const response = await fetch(test.url)
          const data = await response.json()
          testResults[test.name] = {
            status: response.status,
            success: response.ok,
            data: data
          }
        } catch (error) {
          testResults[test.name] = {
            status: 'error',
            success: false,
            error: error.message
          }
        }
      }
      
      setResults(testResults)
      setStatus('complete')
    }

    testApi()
  }, [])

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-lg">
      <h2 className="text-2xl font-bold mb-4">API Connection Test</h2>
      
      {status === 'testing' && (
        <div className="flex items-center space-x-2">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
          <span>Testing API connections...</span>
        </div>
      )}
      
      {status === 'complete' && (
        <div className="space-y-4">
          {Object.entries(results).map(([name, result]) => (
            <div key={name} className="border rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold">{name}</h3>
                <span className={`px-2 py-1 rounded text-sm ${
                  result.success 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-red-100 text-red-800'
                }`}>
                  {result.success ? 'Success' : 'Failed'}
                </span>
              </div>
              
              <div className="text-sm text-gray-600">
                Status: {result.status}
              </div>
              
              {result.error && (
                <div className="text-sm text-red-600 mt-1">
                  Error: {result.error}
                </div>
              )}
              
              {result.data && (
                <details className="mt-2">
                  <summary className="cursor-pointer text-sm text-blue-600">
                    View Response
                  </summary>
                  <pre className="mt-2 text-xs bg-gray-100 p-2 rounded overflow-x-auto">
                    {JSON.stringify(result.data, null, 2)}
                  </pre>
                </details>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ApiTest
