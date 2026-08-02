import React, { useState, useEffect } from 'react';
import { ArrowUpRight, Award, Crown, X } from 'lucide-react';

interface Report {
  topic: string;
  created_at: string;
  report_name: string;
  pdf_name: string | null;
}

interface DashboardData {
  username: string;
  reports: Report[];
}

export default function App() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [dashboardOpen, setDashboardOpen] = useState(false);
  const [username, setUsername] = useState('User');
  const [reports, setReports] = useState<Report[]>([]);
  const [topic, setTopic] = useState('');
  const [numPages, setNumPages] = useState(3);
  const [wantPdf, setWantPdf] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // Fetch dashboard data
  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = () => {
    fetch('/api/dashboard-data')
      .then((res) => {
        if (!res.ok) {
          throw new Error('Not logged in or error');
        }
        return res.json();
      })
      .then((data: DashboardData) => {
        setUsername(data.username);
        setReports(data.reports);
      })
      .catch((err) => {
        console.warn('Backend connection unavailable, using demo mode:', err);
        // Mock data for development
        setUsername('Het Parekh');
        setReports([
          {
            topic: 'Creative Branding Strategies for 2026',
            created_at: '2026-07-24 18:30:12',
            report_name: 'branding_strategy.docx',
            pdf_name: 'branding_strategy.pdf'
          },
          {
            topic: 'UX Design Trends in Augmented Reality',
            created_at: '2026-07-24 16:15:45',
            report_name: 'ux_ar_trends.docx',
            pdf_name: null
          }
        ]);
      });
  };

  const handleGenerate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) {
      setErrorMessage('Please enter a topic first.');
      return;
    }

    setErrorMessage('');
    setSuccessMessage('');
    setIsGenerating(true);

    fetch('/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        topic: topic.trim(),
        num_pages: numPages,
        want_pdf: wantPdf,
      }),
    })
      .then((res) => {
        if (!res.ok) {
          return res.json().then((data) => {
            throw new Error(data.error || 'Failed to generate report.');
          });
        }
        return res.json();
      })
      .then((data) => {
        setSuccessMessage(`Success! Generated: ${data.docx_filename}`);
        setTopic('');
        setIsGenerating(false);
        fetchDashboardData(); // Reload history
      })
      .catch((err) => {
        setErrorMessage(err.message || 'An error occurred.');
        setIsGenerating(false);
      });
  };

  // Stagger animation delays helper
  const getDelayStyle = (i: number) => {
    return {
      transitionDelay: `${i * 80 + 100}ms`
    };
  };

  return (
    <div className="relative w-screen h-screen overflow-hidden text-white font-inter select-none">
      
      {/* Background Video */}
      <video
        autoPlay
        muted
        loop
        playsInline
        className="absolute top-0 left-0 w-full h-full object-cover -z-20 scale-105"
      >
        <source
          src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260606_154941_df1a96e1-a06f-450c-bd02-d863414cc1a0.mp4"
          type="video/mp4"
        />
      </video>
      
      {/* Dark overlay for readability */}
      <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-r from-black/80 via-black/50 to-black/30 -z-10" />

      {/* Navbar */}
      <nav className="absolute top-0 left-0 right-0 flex items-center justify-between z-30 px-6 sm:px-10 lg:px-16 py-5 lg:py-7">
        {/* Brand Logo */}
        <div className="font-podium text-2xl sm:text-3xl font-bold uppercase tracking-wider text-white">
          RETRON
        </div>

        {/* Center Nav Links - hidden on mobile */}
        <div className="hidden md:flex items-center gap-8 lg:gap-12">
          {['Projects', 'Studio', 'Offerings', 'Inquire'].map((link) => (
            <button
              key={link}
              onClick={() => {
                if (link === 'Inquire') {
                  setDashboardOpen(true);
                } else {
                  alert(`${link} page is coming soon.`);
                }
              }}
              className="text-xs lg:text-sm text-white/80 font-medium uppercase tracking-widest hover:text-white transition-colors duration-300"
            >
              {link}
            </button>
          ))}
        </div>

        {/* Right CTA / Hamburger */}
        <div className="flex items-center gap-4">
          {/* Dashboard Toggle Button (Always visible on desktop, or GET IN TOUCH) */}
          <button
            onClick={() => setDashboardOpen(true)}
            className="hidden md:flex items-center gap-2 border border-white/30 hover:border-white/60 px-6 py-3 text-xs font-semibold tracking-widest uppercase hover:bg-white/10 transition-all duration-300 rounded-none"
          >
            GET IN TOUCH
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>

          {/* User Name badge in desktop navbar */}
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-white/10 backdrop-blur-md border border-white/10 text-xs tracking-widest uppercase font-semibold">
            <span className="w-2 h-2 bg-purple-500 rounded-full animate-pulse"></span>
            {username}
          </div>

          {/* Hamburger Menu Button for mobile */}
          <button
            onClick={() => setMenuOpen(true)}
            className="flex md:hidden flex-col gap-1.5 p-2 bg-transparent border-0 outline-none cursor-pointer"
            aria-label="Toggle menu"
          >
            <div className="w-6 h-0.5 bg-white"></div>
            <div className="w-6 h-0.5 bg-white"></div>
            <div className="w-4 h-0.5 bg-white self-end"></div>
          </button>
        </div>
      </nav>

      {/* Mobile Menu Overlay */}
      <div
        className={`fixed inset-0 z-50 bg-black/95 backdrop-blur-md flex flex-col justify-between transition-all duration-500 ease-in-out ${
          menuOpen ? 'opacity-100 visible' : 'opacity-0 invisible pointer-events-none'
        }`}
      >
        {/* Header row in mobile overlay */}
        <div className="flex items-center justify-between px-6 sm:px-10 py-5">
          <div className="font-podium text-2xl sm:text-3xl font-bold uppercase tracking-wider">
            RETRON
          </div>
          <button
            onClick={() => setMenuOpen(false)}
            className="p-2 border-0 bg-transparent text-white cursor-pointer hover:text-purple-400 transition-colors"
            aria-label="Close menu"
          >
            <X className="w-7 h-7" />
          </button>
        </div>

        {/* Navigation Links */}
        <div className="flex flex-col items-center justify-center gap-8 py-10">
          {['Projects', 'Studio', 'Offerings', 'Inquire'].map((link, i) => (
            <button
              key={link}
              onClick={() => {
                setMenuOpen(false);
                if (link === 'Inquire') {
                  setTimeout(() => setDashboardOpen(true), 300);
                } else {
                  alert(`${link} page is coming soon.`);
                }
              }}
              style={menuOpen ? getDelayStyle(i) : undefined}
              className={`font-podium text-4xl sm:text-5xl uppercase tracking-widest text-white hover:text-purple-400 transition-all duration-500 transform ${
                menuOpen ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-5'
              }`}
            >
              {link}
            </button>
          ))}
        </div>

        {/* Get In Touch Button in mobile overlay */}
        <div className="flex flex-col items-center pb-16 px-6">
          <button
            onClick={() => {
              setMenuOpen(false);
              setTimeout(() => setDashboardOpen(true), 300);
            }}
            style={menuOpen ? getDelayStyle(4) : undefined}
            className={`flex items-center justify-center gap-2 border border-white/30 hover:border-white/60 w-full max-w-xs py-4 text-xs font-bold tracking-widest uppercase hover:bg-white/10 transition-all duration-500 transform ${
              menuOpen ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-5'
            }`}
          >
            GET IN TOUCH
            <ArrowUpRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Hero Content (Vertically centered, left-aligned) */}
      <main className="h-full w-full flex flex-col justify-center px-6 sm:px-12 lg:px-20 max-w-4xl select-none">
        
        {/* Tagline */}
        <div className="animate-fade-up flex items-center gap-2.5 mb-6 lg:mb-8">
          <Crown className="w-4 h-4 text-white/70" />
          <span className="text-white/70 text-xs sm:text-sm font-semibold tracking-[0.3em] uppercase">
            
          </span>
        </div>

        {/* Main Heading */}
        <h1 className="animate-fade-up-delay-1 font-podium text-white uppercase leading-[0.92] tracking-tight text-[clamp(2.8rem,7.5vw,6.5rem)] flex flex-col mb-6">
          <span>Make.</span>
          <span>Free.</span>
          <span>Reports.</span>
        </h1>

        {/* Subtext */}
        <p className="animate-fade-up-delay-2 text-white/70 text-sm sm:text-base leading-relaxed max-w-md mt-2">
          Just enter the topic and we will make a <br />
          professional Word report -- <strong className="text-white font-bold">in seconds.</strong>
        </p>

        {/* CTA Row */}
        <div className="animate-fade-up-delay-3 flex flex-wrap items-center gap-4 sm:gap-6 mt-8 lg:mt-10">
          <button
            onClick={() => setDashboardOpen(true)}
            className="group flex items-center gap-2 bg-black hover:bg-neutral-900 text-white font-bold border border-neutral-800 px-6 sm:px-8 py-3.5 sm:py-4 text-[10px] sm:text-xs tracking-widest uppercase transition-all duration-300"
          >
            GET STARTED
            <ArrowUpRight className="w-4 h-4 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform duration-300" />
          </button>

          <div className="hidden sm:flex items-center gap-3">
            <Award className="w-8 h-8 text-white/50" />
            <div className="text-white/60 text-[10px] sm:text-xs tracking-widest uppercase font-semibold leading-tight">
              <div>Made By</div>
              <div>Het</div>
            </div>
          </div>
        </div>

        {/* Stats Row */}
        <div className="animate-fade-up-delay-4 flex flex-wrap gap-8 sm:gap-12 lg:gap-16 mt-8 sm:mt-10 lg:mt-14 border-t border-white/10 pt-6 max-w-2xl">
          {[
            { value: '24/7', label: 'Works' },
            { value: '100%', label: 'AI Used' },
            { value: '50+', label: 'Pages Also' }
          ].map((stat, idx) => (
            <div key={idx} className="flex flex-col">
              <span className="font-semibold text-white text-2xl sm:text-3xl lg:text-4xl tracking-tight">
                {stat.value}
              </span>
              <span className="text-white/50 text-[9px] sm:text-xs tracking-widest uppercase mt-1">
                {stat.label}
              </span>
            </div>
          ))}
        </div>
      </main>

      {/* Interactive Dashboard / Report Generator Drawer */}
      <div
        className={`fixed top-0 right-0 h-full w-full sm:w-[480px] bg-neutral-950/90 backdrop-blur-xl border-l border-white/10 z-40 flex flex-col justify-between transition-transform duration-500 ease-out shadow-2xl ${
          dashboardOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {/* Drawer Header */}
        <div className="p-6 border-b border-white/10 flex items-center justify-between bg-black/30">
          <div>
            <h2 className="font-podium text-xl tracking-wider uppercase text-white">
              REPORT CENTER
            </h2>
            <div className="text-xs text-white/60 mt-1">
              Active Session: <strong className="text-purple-400 font-semibold">{username}</strong>
            </div>
          </div>
          <button
            onClick={() => setDashboardOpen(false)}
            className="p-2 border-0 bg-transparent text-white/70 hover:text-white cursor-pointer transition-colors"
            aria-label="Close dashboard"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Drawer Body - Scrollable content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-8 custom-scrollbar">
          
          {/* Report Generator Input Form */}
          <div className="bg-white/5 border border-white/10 p-5 rounded-none backdrop-blur-md">
            <h3 className="text-xs tracking-[0.2em] uppercase font-bold text-purple-400 mb-4 flex items-center gap-1.5">
              <Crown className="w-3.5 h-3.5" />
              Generate AI Report
            </h3>

            <form onSubmit={handleGenerate} className="space-y-5">
              {/* Premium Input Layout */}
              <div className="relative group">
                <input
                  type="text"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="Enter branding topic or research subject..."
                  disabled={isGenerating}
                  className="w-full bg-neutral-900/60 border border-white/20 hover:border-white/40 focus:border-purple-500 text-white placeholder-white/40 px-4 py-3.5 text-sm transition-colors rounded-none outline-none"
                />
              </div>

              {/* Slider for Page Count */}
              <div className="space-y-2">
                <div className="flex justify-between text-xs tracking-wider text-white/70 uppercase">
                  <span>Report Length (Pages)</span>
                  <span className="text-white font-bold">{numPages}</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="50"
                  value={numPages}
                  onChange={(e) => setNumPages(parseInt(e.target.value))}
                  disabled={isGenerating}
                  className="w-full h-1 bg-white/20 rounded-lg appearance-none cursor-pointer accent-purple-500"
                />
              </div>

              {/* Checkboxes and options */}
              <div className="flex items-center gap-2.5">
                <input
                  type="checkbox"
                  id="pdf"
                  checked={wantPdf}
                  onChange={(e) => setWantPdf(e.target.checked)}
                  disabled={isGenerating}
                  className="w-4 h-4 rounded-none bg-neutral-900 border-white/20 text-purple-500 focus:ring-0 focus:ring-offset-0 cursor-pointer"
                />
                <label
                  htmlFor="pdf"
                  className="text-xs tracking-wider text-white/80 uppercase select-none cursor-pointer"
                >
                  Also Generate PDF Format
                </label>
              </div>

              {/* Status messages */}
              {errorMessage && (
                <div className="p-3 bg-red-950/40 border border-red-800/40 text-red-300 text-xs">
                  {errorMessage}
                </div>
              )}
              {successMessage && (
                <div className="p-3 bg-green-950/40 border border-green-800/40 text-green-300 text-xs">
                  {successMessage}
                </div>
              )}

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isGenerating}
                className={`w-full py-4 text-xs font-bold tracking-widest uppercase border transition-all duration-300 rounded-none ${
                  isGenerating
                    ? 'bg-neutral-800 text-white/50 border-neutral-700 cursor-not-allowed'
                    : 'bg-white text-black hover:bg-neutral-200 border-white font-bold'
                }`}
              >
                {isGenerating ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="w-3.5 h-3.5 border-2 border-white/20 border-t-white rounded-full animate-spin"></span>
                    Analyzing Topic & Formatting...
                  </span>
                ) : (
                  'INITIATE GENERATION'
                )}
              </button>
            </form>
          </div>

          {/* Recent Reports List */}
          <div className="space-y-4">
            <h3 className="text-xs tracking-[0.2em] uppercase font-bold text-white/50">
              Recent Activity
            </h3>

            {reports.length === 0 ? (
              <div className="text-center py-8 text-xs text-white/30 border border-dashed border-white/10">
                No reports generated yet.
              </div>
            ) : (
              <div className="space-y-3">
                {reports.map((report, idx) => (
                  <div
                    key={idx}
                    className="p-4 bg-white/5 border border-white/10 hover:border-white/20 transition-all flex flex-col justify-between gap-3 animate-fade-in"
                  >
                    <div>
                      <h4 className="text-sm font-semibold text-white/90 line-clamp-1">
                        {report.topic}
                      </h4>
                      <p className="text-[10px] text-white/40 mt-1">
                        {report.created_at}
                      </p>
                    </div>

                    <div className="flex items-center gap-3 pt-2 border-t border-white/5">
                      <a
                        href={`/download/${report.report_name}`}
                        className="text-[10px] font-bold tracking-widest uppercase bg-white/10 hover:bg-white text-white hover:text-black border border-white/15 px-3 py-1.5 transition-all"
                      >
                        DOCX
                      </a>
                      {report.pdf_name && (
                        <a
                          href={`/download/${report.pdf_name}`}
                          className="text-[10px] font-bold tracking-widest uppercase bg-purple-500/20 hover:bg-purple-500 text-purple-200 hover:text-white border border-purple-500/30 px-3 py-1.5 transition-all"
                        >
                          PDF
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Drawer Footer */}
        <div className="p-4 border-t border-white/10 bg-black/40 flex justify-between items-center text-xs">
          <a
            href="/history"
            className="text-white/60 hover:text-white tracking-widest uppercase hover:underline"
          >
            Full History
          </a>
          <a
            href="/logout"
            className="text-red-400/80 hover:text-red-400 tracking-widest uppercase hover:underline"
          >
            Log Out
          </a>
        </div>
      </div>
    </div>
  );
}
