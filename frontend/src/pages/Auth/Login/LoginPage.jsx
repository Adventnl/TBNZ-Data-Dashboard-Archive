import React, { useState } from 'react';
import './LoginPage.css';
import { useNavigate } from 'react-router-dom';

export default function LoginPage() {
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    username: '',
    password: '',
    trustDevice: false,
  });

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');

    if (!formData.username.trim() || !formData.password.trim()) {
      setErrorMsg('Please enter your username and password');
      return;
    }

    try {
      setLoading(true);

      const params = new URLSearchParams();
      params.append('username', formData.username);
      params.append('password', formData.password);

      const response = await fetch(`${import.meta.env.VITE_API_BASE || 'http://localhost:8000/api'}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: params.toString(),
      });
      console.log(response)
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Login failed');
      }

      // 保存 token
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('token_type', data.token_type || 'bearer');

      navigate('/map')

      // 如果你后面想记住设备，也可以顺手存一下
      if (formData.trustDevice) {
        localStorage.setItem('trustDevice', 'true');
      } else {
        localStorage.removeItem('trustDevice');
      }

      console.log('Login success:', data);

      // 这里后面可以改成你的页面跳转
      // 例如：
      // window.location.href = '/dashboard';

    } catch (error) {
      console.error('Login failed:', error);
      setErrorMsg(error.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-wrapper">
        {/* Left */}
        <div className="login-left">
          <div className="login-brand">
            Tiger &nbsp;<span>Brokers</span>
          </div>

          <div className="login-visual-card">
            <div className="login-image-wrap">
              <img
                src="login-info.jpg"
                alt="Tiger visual"
                className="login-image"
              />
            </div>

            <div className="login-visual-footer">TIGER TRADE</div>
          </div>
        </div>

        {/* Right */}
        <div className="login-right">
          <div className="login-form-wrapper">
            <div className="login-form-box">
              <p className="login-title">Sign in</p>
              <p className="login-subtitle">
                Access your global investment portfolio
              </p>

              <form onSubmit={handleSubmit}>
                <div className="login-form-group">
                  <label>Username </label>
                  <div className="login-input-box">
                    <img src="/user.png" className="login-input-icon" alt="user" />
                    <input
                      type="text"
                      name="username"
                      placeholder="Enter your username or email"
                      value={formData.username}
                      onChange={handleChange}
                    />
                  </div>
                </div>

                <div className="login-form-group">
                  <label>Password</label>
                  <div className="login-input-box">
                    <img src="/lock.png" className="login-input-icon" alt="lock" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      name="password"
                      placeholder="••••••••••••"
                      value={formData.password}
                      onChange={handleChange}
                    />
                    <button
                      type="button"
                      className="login-eye-btn"
                      onClick={() => setShowPassword((prev) => !prev)}
                    >
                      <img
                        src={showPassword ? '/show.png' : '/hidden.png'}
                        alt="toggle password"
                        className="eye-icon"
                      />
                    </button>
                  </div>
                </div>

                <div className="login-options">
                  <label className="login-checkbox-wrap">
                    <input
                      type="checkbox"
                      name="trustDevice"
                      checked={formData.trustDevice}
                      onChange={handleChange}
                    />
                    <span>Trust this device</span>
                  </label>
                </div>

                {errorMsg && <p className="login-error-text">{errorMsg}</p>}

                <button
                  type="submit"
                  className="login-signin-btn"
                  disabled={loading}
                >
                  {loading ? 'Signing In...' : 'Sign In'}
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}