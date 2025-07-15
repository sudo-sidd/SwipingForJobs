import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import sessionManager from './sessionManager';

const API_BASE_URL = 'http://localhost:8000';

const GitHubCallback = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('processing');
  const [message, setMessage] = useState('Processing GitHub authentication...');
  const [githubUser, setGithubUser] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    handleGitHubCallback();
  }, []);

  const handleGitHubCallback = async () => {
    try {
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const error = searchParams.get('error');

      if (error) {
        setStatus('error');
        setMessage(`GitHub authentication error: ${error}`);
        return;
      }

      if (!code) {
        setStatus('error');
        setMessage('No authorization code received from GitHub');
        return;
      }

      // Validate state parameter
      const storedState = sessionStorage.getItem('github_oauth_state');
      if (!storedState || storedState !== state) {
        setStatus('error');
        setMessage('Invalid state parameter. Please try again.');
        return;
      }

      // Get the user ID that initiated the OAuth flow
      const linkingUserId = sessionStorage.getItem('github_linking_user_id');
      if (!linkingUserId) {
        setStatus('error');
        setMessage('No user session found. Please try again.');
        return;
      }

      // Exchange code for token and user info
      const callbackResponse = await fetch(`${API_BASE_URL}/auth/github/callback?code=${code}&state=${state}`);
      
      if (!callbackResponse.ok) {
        const errorData = await callbackResponse.json();
        throw new Error(errorData.detail || 'Failed to process GitHub callback');
      }

      const callbackData = await callbackResponse.json();

      if (callbackData.github_linked) {
        // User was already linked, redirect to profile
        setStatus('success');
        setMessage('GitHub account linked successfully!');
        
        // Clean up session storage
        sessionStorage.removeItem('github_oauth_state');
        sessionStorage.removeItem('github_linking_user_id');
        
        // Redirect to profile after a short delay
        setTimeout(() => {
          navigate('/profile');
        }, 2000);
      } else {
        // Need to link the account
        setGithubUser(callbackData.github_user);
        setStatus('linking');
        setMessage('Linking GitHub account to your profile...');
        
        // Link the account
        await linkGitHubAccount(linkingUserId, callbackData.github_user, callbackData.access_token);
      }

    } catch (error) {
      console.error('GitHub callback error:', error);
      setStatus('error');
      setError(error.message);
      setMessage('Failed to process GitHub authentication');
    }
  };

  const linkGitHubAccount = async (userId, githubUser, accessToken) => {
    try {
      const linkResponse = await fetch(`${API_BASE_URL}/auth/github/link`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...sessionManager.getAuthHeaders()
        },
        body: JSON.stringify({
          user_id: parseInt(userId),
          github_id: githubUser.id,
          access_token: accessToken,
          github_username: githubUser.username
        })
      });

      if (!linkResponse.ok) {
        const errorData = await linkResponse.json();
        throw new Error(errorData.detail || 'Failed to link GitHub account');
      }

      const linkData = await linkResponse.json();
      
      setStatus('success');
      setMessage('GitHub account linked successfully!');
      
      // Clean up session storage
      sessionStorage.removeItem('github_oauth_state');
      sessionStorage.removeItem('github_linking_user_id');
      
      // Redirect to profile after a short delay
      setTimeout(() => {
        navigate('/profile');
      }, 2000);

    } catch (error) {
      console.error('GitHub linking error:', error);
      setStatus('error');
      setError(error.message);
      setMessage('Failed to link GitHub account');
    }
  };

  const handleRetry = () => {
    // Clean up session storage
    sessionStorage.removeItem('github_oauth_state');
    sessionStorage.removeItem('github_linking_user_id');
    
    // Redirect back to profile
    navigate('/profile');
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          <div className="text-center">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-blue-100">
              <svg className="h-6 w-6 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 0C4.477 0 0 4.484 0 10.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0110 4.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.203 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.942.359.31.678.921.678 1.856 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0020 10.017C20 4.484 15.522 0 10 0z" clipRule="evenodd" />
              </svg>
            </div>
            
            <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
              GitHub Integration
            </h2>
            
            <div className="mt-6">
              {status === 'processing' && (
                <div className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span className="text-sm text-gray-600">{message}</span>
                </div>
              )}
              
              {status === 'linking' && (
                <div className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <div className="text-left">
                    <p className="text-sm text-gray-600">{message}</p>
                    {githubUser && (
                      <p className="text-xs text-gray-500 mt-1">
                        Linking @{githubUser.username} to your account...
                      </p>
                    )}
                  </div>
                </div>
              )}
              
              {status === 'success' && (
                <div className="text-center">
                  <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100">
                    <svg className="h-6 w-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <h3 className="mt-2 text-lg font-medium text-gray-900">Success!</h3>
                  <p className="mt-1 text-sm text-gray-600">{message}</p>
                  <p className="mt-1 text-xs text-gray-500">Redirecting to your profile...</p>
                </div>
              )}
              
              {status === 'error' && (
                <div className="text-center">
                  <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100">
                    <svg className="h-6 w-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </div>
                  <h3 className="mt-2 text-lg font-medium text-gray-900">Error</h3>
                  <p className="mt-1 text-sm text-gray-600">{message}</p>
                  {error && (
                    <p className="mt-1 text-xs text-red-600">{error}</p>
                  )}
                  <button
                    onClick={handleRetry}
                    className="mt-4 w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  >
                    Try Again
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GitHubCallback;
