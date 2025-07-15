import React, { useState, useEffect } from 'react';
import sessionManager from './sessionManager';

const API_BASE_URL = 'http://localhost:8000';

const GitHubIntegration = ({ userData, onUpdate }) => {
  const [githubStatus, setGithubStatus] = useState({
    github_linked: false,
    github_username: null,
    linked_at: null,
    repos_count: 0
  });
  const [loading, setLoading] = useState(true);
  const [linking, setLinking] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [repos, setRepos] = useState([]);
  const [showRepos, setShowRepos] = useState(false);
  const [githubData, setGithubData] = useState(null);

  useEffect(() => {
    fetchGitHubStatus();
  }, [userData.id]);

  const fetchGitHubStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/github/status/${userData.id}`, {
        headers: sessionManager.getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        setGithubStatus(data);
      }
    } catch (error) {
      console.error('Error fetching GitHub status:', error);
    } finally {
      setLoading(false);
    }
  };

  const initiateGitHubLogin = async () => {
    try {
      setLinking(true);
      
      const response = await fetch(`${API_BASE_URL}/auth/github/login`);
      
      if (response.ok) {
        const data = await response.json();
        
        // Store state for validation
        sessionStorage.setItem('github_oauth_state', data.state);
        sessionStorage.setItem('github_linking_user_id', userData.id);
        
        // Redirect to GitHub OAuth
        window.location.href = data.auth_url;
      } else {
        throw new Error('Failed to initiate GitHub login');
      }
    } catch (error) {
      console.error('Error initiating GitHub login:', error);
      alert('Failed to initiate GitHub login. Please try again.');
    } finally {
      setLinking(false);
    }
  };

  const unlinkGitHub = async () => {
    if (!confirm('Are you sure you want to unlink your GitHub account? This will remove all synced repository data.')) {
      return;
    }

    try {
      setLinking(true);
      
      const response = await fetch(`${API_BASE_URL}/auth/github/unlink/${userData.id}`, {
        method: 'POST',
        headers: sessionManager.getAuthHeaders()
      });

      if (response.ok) {
        setGithubStatus({
          github_linked: false,
          github_username: null,
          linked_at: null,
          repos_count: 0
        });
        setRepos([]);
        setShowRepos(false);
        alert('GitHub account unlinked successfully');
      } else {
        throw new Error('Failed to unlink GitHub account');
      }
    } catch (error) {
      console.error('Error unlinking GitHub:', error);
      alert('Failed to unlink GitHub account. Please try again.');
    } finally {
      setLinking(false);
    }
  };

  const refreshGitHubData = async () => {
    try {
      setRefreshing(true);
      
      const response = await fetch(`${API_BASE_URL}/auth/github/refresh/${userData.id}`, {
        method: 'POST',
        headers: sessionManager.getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        await fetchGitHubStatus();
        alert(`GitHub data refreshed successfully. ${data.repos_count} repositories synced.`);
      } else {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to refresh GitHub data');
      }
    } catch (error) {
      console.error('Error refreshing GitHub data:', error);
      alert('Failed to refresh GitHub data. Please try again.');
    } finally {
      setRefreshing(false);
    }
  };

  const fetchRepos = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/github/repos/${userData.id}`, {
        headers: sessionManager.getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        setRepos(data.repos);
        setShowRepos(true);
      } else {
        throw new Error('Failed to fetch repositories');
      }
    } catch (error) {
      console.error('Error fetching repos:', error);
      alert('Failed to fetch repositories. Please try again.');
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  const getTopLanguages = (languages) => {
    if (!languages || Object.keys(languages).length === 0) return [];
    
    return Object.entries(languages)
      .sort(([,a], [,b]) => b.percentage - a.percentage)
      .slice(0, 3)
      .map(([lang, data]) => ({
        name: lang,
        percentage: data.percentage.toFixed(1)
      }));
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center space-x-3 mb-4">
          <div className="w-6 h-6 bg-gray-300 rounded animate-pulse"></div>
          <div className="h-6 bg-gray-300 rounded w-32 animate-pulse"></div>
        </div>
        <div className="h-4 bg-gray-200 rounded w-full animate-pulse"></div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <svg className="w-6 h-6 text-gray-700" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 0C4.477 0 0 4.484 0 10.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0110 4.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.203 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.942.359.31.678.921.678 1.856 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0020 10.017C20 4.484 15.522 0 10 0z" clipRule="evenodd" />
          </svg>
          <h3 className="text-lg font-semibold text-gray-900">GitHub Integration</h3>
        </div>
        
        {githubStatus.github_linked && (
          <div className="flex items-center space-x-2">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
              ✓ Linked
            </span>
          </div>
        )}
      </div>

      {githubStatus.github_linked ? (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-600">GitHub Username</p>
              <p className="font-medium text-gray-900">@{githubStatus.github_username}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Repositories</p>
              <p className="font-medium text-gray-900">{githubStatus.repos_count} repos</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Linked On</p>
              <p className="font-medium text-gray-900">{formatDate(githubStatus.linked_at)}</p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              onClick={fetchRepos}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
            >
              {showRepos ? 'Hide Repositories' : 'Show Repositories'}
            </button>
            
            <button
              onClick={refreshGitHubData}
              disabled={refreshing}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50"
            >
              {refreshing ? 'Refreshing...' : 'Refresh Data'}
            </button>
            
            <button
              onClick={unlinkGitHub}
              disabled={linking}
              className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50"
            >
              {linking ? 'Unlinking...' : 'Unlink GitHub'}
            </button>
          </div>

          {showRepos && (
            <div className="mt-6">
              <h4 className="text-md font-medium text-gray-900 mb-3">Your Repositories</h4>
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {repos.map((repo) => (
                  <div key={repo.id} className="border rounded-lg p-4 hover:bg-gray-50">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h5 className="font-medium text-gray-900">
                          <a
                            href={repo.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:text-blue-600"
                          >
                            {repo.name}
                          </a>
                        </h5>
                        {repo.description && (
                          <p className="text-sm text-gray-600 mt-1">{repo.description}</p>
                        )}
                        
                        <div className="flex items-center space-x-4 mt-2 text-sm text-gray-500">
                          {repo.language && (
                            <span className="flex items-center">
                              <span className="w-3 h-3 rounded-full bg-blue-500 mr-1"></span>
                              {repo.language}
                            </span>
                          )}
                          <span>⭐ {repo.stars}</span>
                          <span>🍴 {repo.forks}</span>
                          <span>Updated {formatDate(repo.updated_at)}</span>
                        </div>

                        {repo.languages && Object.keys(repo.languages).length > 0 && (
                          <div className="mt-2">
                            <div className="flex flex-wrap gap-1">
                              {getTopLanguages(repo.languages).map((lang) => (
                                <span
                                  key={lang.name}
                                  className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800"
                                >
                                  {lang.name} ({lang.percentage}%)
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="text-center py-8">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">No GitHub account linked</h3>
          <p className="mt-1 text-sm text-gray-500">
            Connect your GitHub account to showcase your repositories and projects.
          </p>
          <div className="mt-6">
            <button
              onClick={initiateGitHubLogin}
              disabled={linking}
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-gray-900 hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 disabled:opacity-50"
            >
              {linking ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Connecting...
                </>
              ) : (
                <>
                  <svg className="-ml-1 mr-2 h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 0C4.477 0 0 4.484 0 10.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0110 4.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.203 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.942.359.31.678.921.678 1.856 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0020 10.017C20 4.484 15.522 0 10 0z" clipRule="evenodd" />
                  </svg>
                  Connect GitHub
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default GitHubIntegration;
