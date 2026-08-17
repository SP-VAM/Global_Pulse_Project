import React, { useState, useEffect, useRef } from "react";
import ReactDOM from "react-dom";
import { X, ExternalLink, Play, Pause, CheckCircle2 } from "lucide-react";

/**
 * LearningModal Component
 * Embedded 16:9 YouTube video player modal with real-time watch progress tracking,
 * 90% completion threshold auto-detection, and CC caption support.
 * 
 * @param {Object} props
 * @param {Object} props.course - Currently selected course object
 * @param {Function} props.onClose - Close modal handler
 * @param {Object} [props.existingProgress] - Previously saved watch progress { progressSeconds, progressPercentage, isCompleted }
 * @param {Function} [props.onSaveProgress] - Callback function to persist watch progress
 */
export default function LearningModal({ course, onClose, existingProgress, onSaveProgress }) {
  const totalDurationSeconds = course?.durationSeconds || 1800;
  
  const iframeRef = useRef(null);

  // Initial position from existing progress
  const [currentSeconds, setCurrentSeconds] = useState(
    existingProgress?.progressSeconds || 0
  );
  const [isPlaying, setIsPlaying] = useState(true);
  const [isCompleted, setIsCompleted] = useState(
    existingProgress?.isCompleted || (existingProgress?.progressPercentage >= 90) || false
  );

  // Keep ref for current values to save on unmount/close
  const progressRef = useRef({ currentSeconds, totalDurationSeconds, isCompleted });

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") handleClose();
    };

    if (course) {
      document.addEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "unset";
    };
  }, [course]);

  // Subscribe to YouTube iframe API events to detect play, pause, and seek changes (BUG-09)
  useEffect(() => {
    const handleMessage = (event) => {
      if (!event.origin.includes("youtube.com")) return;
      try {
        const data = typeof event.data === "string" ? JSON.parse(event.data) : event.data;
        if (data) {
          let state = null;
          if (data.event === "onStateChange") {
            state = data.info;
          } else if (data.event === "infoDelivery" && data.info) {
            if (data.info.playerState !== undefined) {
              state = data.info.playerState;
            }
            if (data.info.currentTime !== undefined) {
              const time = Math.round(data.info.currentTime);
              setCurrentSeconds(time);
              
              const nextPct = Math.round((time / totalDurationSeconds) * 100);
              if (nextPct >= 90) {
                setIsCompleted(true);
              }
              
              progressRef.current = {
                currentSeconds: time,
                totalDurationSeconds,
                isCompleted: isCompleted || nextPct >= 90,
                pct: nextPct,
              };
            }
          }
          
          if (state !== null) {
            if (state === 1) {
              setIsPlaying(true);
            } else if (state === 2 || state === 0) {
              setIsPlaying(false);
            }
          }
        }
      } catch (err) {
        // Not a JSON message or not from YouTube
      }
    };
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [totalDurationSeconds, isCompleted]);

  // Toggle play / pause and send command to YouTube iframe
  const togglePlayPause = () => {
    const nextState = !isPlaying;
    setIsPlaying(nextState);
    if (iframeRef.current && iframeRef.current.contentWindow) {
      const command = nextState ? "playVideo" : "pauseVideo";
      iframeRef.current.contentWindow.postMessage(
        JSON.stringify({ event: "command", func: command, args: "" }),
        "*"
      );
    }
  };

  // Real-time watch position timer simulation while player modal is active
  useEffect(() => {
    let timer;
    if (isPlaying && course) {
      timer = setInterval(() => {
        setCurrentSeconds((prev) => {
          const next = Math.min(totalDurationSeconds, prev + 2);
          const nextPct = Math.round((next / totalDurationSeconds) * 100);
          
          // Check 90% completion threshold (Test Scenario TS_FRD046_Completion_1)
          if (nextPct >= 90 && !isCompleted) {
            setIsCompleted(true);
          }

          progressRef.current = {
            currentSeconds: next,
            totalDurationSeconds,
            isCompleted: isCompleted || nextPct >= 90,
            pct: nextPct,
          };
          
          return next;
        });
      }, 1000);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isPlaying, course, totalDurationSeconds, isCompleted]);

  // Save progress when component unmounts or modal closes
  const handleClose = () => {
    const pct = Math.round((currentSeconds / totalDurationSeconds) * 100);
    const completed = isCompleted || pct >= 90;
    if (onSaveProgress && course) {
      onSaveProgress(course.id, currentSeconds, totalDurationSeconds, pct, completed);
    }
    onClose();
  };

  // Autosave progress on abrupt tab/window close (TC-14)
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (course && onSaveProgress) {
        const { currentSeconds, totalDurationSeconds, isCompleted, pct } = progressRef.current;
        onSaveProgress(course.id, currentSeconds, totalDurationSeconds, pct || 0, isCompleted);
      }
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, [course, onSaveProgress]);

  if (!course) return null;

  const pct = Math.round((currentSeconds / totalDurationSeconds) * 100);

  // Include enablejsapi=1 and start timestamp for YouTube API control
  const startSec = existingProgress?.progressSeconds || 0;
  const embedSrc =
    course.embedUrl
      ? `${course.embedUrl}${course.embedUrl.includes("?") ? "&" : "?"}enablejsapi=1${startSec > 0 ? `&start=${startSec}` : ""}`
      : course.videoId
      ? `https://www.youtube.com/embed/${course.videoId}?autoplay=1&cc_load_policy=1&enablejsapi=1${startSec > 0 ? `&start=${startSec}` : ""}`
      : "";

  const formatTime = (totalSec) => {
    const mins = Math.floor(totalSec / 60);
    const secs = totalSec % 60;
    return `${mins}:${secs < 10 ? "0" : ""}${secs}`;
  };

  return ReactDOM.createPortal(
    <div
      className="modal-overlay"
      onClick={handleClose}
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0, 0, 0, 0.88)",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 99999,
        padding: "16px",
      }}
    >
      <div
        className="lh-video-modal"
        onClick={(e) => e.stopPropagation()}
        style={{
          position: "relative",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          width: "100%",
          maxWidth: "850px",
          borderRadius: "14px",
          background: "#0d111b",
          border: "1px solid rgba(255, 255, 255, 0.12)",
          boxShadow: "0 20px 50px rgba(0, 0, 0, 0.6)",
        }}
      >
        {/* Modal Header */}
        <div
          className="lh-modal-header"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "14px 20px",
            borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
            background: "rgba(13, 17, 27, 0.95)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span
              style={{
                fontSize: "11px",
                fontWeight: "700",
                color: "#38bdf8",
                textTransform: "uppercase",
                letterSpacing: "0.5px",
                padding: "2px 8px",
                borderRadius: "4px",
                background: "rgba(56, 189, 248, 0.12)",
              }}
            >
              {course.level}
            </span>
            <h3
              style={{
                margin: 0,
                fontSize: "15px",
                fontWeight: "700",
                color: "#ffffff",
              }}
            >
              {course.title}
            </h3>
          </div>
          
          <button
            type="button"
            onClick={handleClose}
            style={{
              background: "rgba(255, 255, 255, 0.05)",
              border: "none",
              color: "#94a3b8",
              cursor: "pointer",
              padding: "6px",
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "all 0.2s ease",
            }}
            aria-label="Close modal"
          >
            <X size={18} />
          </button>
        </div>

        {/* 16:9 Video Player Wrapper */}
        <div className="lh-video-wrapper" style={{ position: "relative", width: "100%", paddingTop: "56.25%", background: "#000" }}>
          <iframe
            ref={iframeRef}
            src={embedSrc}
            title={course.title}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              height: "100%",
              border: 0,
            }}
          ></iframe>
        </div>

        {/* Live Playback Control & Progress Bar (Pause / Resume / 90% completion tracker) */}
        <div
          className="lh-modal-controls"
          style={{
            padding: "12px 20px",
            background: "rgba(18, 24, 38, 0.95)",
            borderTop: "1px solid rgba(255, 255, 255, 0.08)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <button
                type="button"
                onClick={togglePlayPause}
                style={{
                  background: isPlaying ? "rgba(56, 189, 248, 0.15)" : "rgba(16, 185, 129, 0.2)",
                  border: `1px solid ${isPlaying ? "rgba(56, 189, 248, 0.4)" : "rgba(16, 185, 129, 0.5)"}`,
                  color: isPlaying ? "#38bdf8" : "#10b981",
                  borderRadius: "6px",
                  padding: "4px 10px",
                  fontSize: "12px",
                  fontWeight: "600",
                  display: "flex",
                  alignItems: "center",
                  gap: "5px",
                  cursor: "pointer"
                }}
              >
                {isPlaying ? <><Pause size={13} /> Pause Progress</> : <><Play size={13} /> Resume Progress</>}
              </button>
              
              <span style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600" }}>
                {formatTime(currentSeconds)} / {formatTime(totalDurationSeconds)} ({pct}%)
              </span>

              {/* Playback State Indicator Badge */}
              <span
                style={{
                  fontSize: "11px",
                  fontWeight: "700",
                  color: isPlaying ? "#06b6d4" : "#f59e0b",
                  background: isPlaying ? "rgba(6, 182, 212, 0.12)" : "rgba(245, 158, 11, 0.12)",
                  border: `1px solid ${isPlaying ? "rgba(6, 182, 212, 0.3)" : "rgba(245, 158, 11, 0.3)"}`,
                  padding: "2px 8px",
                  borderRadius: "4px",
                  textTransform: "uppercase",
                  letterSpacing: "0.5px",
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                  marginLeft: "4px"
                }}
              >
                <span
                  style={{
                    width: "6px",
                    height: "6px",
                    borderRadius: "50%",
                    background: isPlaying ? "#06b6d4" : "#f59e0b",
                    display: "inline-block",
                    animation: isPlaying ? "pulse-playing 1.5s infinite" : "none"
                  }}
                />
                {isPlaying ? "Playing" : "Paused"}
              </span>
            </div>

            {/* 90% Completion threshold badge */}
            {(isCompleted || pct >= 90) ? (
              <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "#10b981", fontSize: "12px", fontWeight: "700", background: "rgba(16, 185, 129, 0.12)", padding: "4px 10px", borderRadius: "6px" }}>
                <CheckCircle2 size={14} /> 90%+ Reached (Module Completed)
              </div>
            ) : (
              <span style={{ fontSize: "11.5px", color: "#64748b" }}>
                Watch {Math.max(0, 90 - pct)}% more to complete module
              </span>
            )}
          </div>

          {/* Interactive Seek/Progress slider */}
          <input
            type="range"
            min="0"
            max={totalDurationSeconds}
            value={currentSeconds}
            onChange={(e) => {
              const val = Number(e.target.value);
              setCurrentSeconds(val);
              const newPct = Math.round((val / totalDurationSeconds) * 100);
              if (newPct >= 90) setIsCompleted(true);

              if (iframeRef.current && iframeRef.current.contentWindow) {
                iframeRef.current.contentWindow.postMessage(
                  JSON.stringify({ event: "command", func: "seekTo", args: [val, true] }),
                  "*"
                );
              }
            }}
            style={{
              width: "100%",
              height: "5px",
              accentColor: isCompleted || pct >= 90 ? "#10b981" : "#38bdf8",
              cursor: "pointer",
            }}
          />
        </div>

        {/* Modal Footer: Description & External YouTube link */}
        <div
          className="lh-modal-footer"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "12px 20px",
            background: "rgba(13, 17, 27, 0.95)",
            borderTop: "1px solid rgba(255, 255, 255, 0.08)",
          }}
        >
          <span style={{ fontSize: "12.5px", color: "#94a3b8" }}>
            {course.description}
          </span>
          {course.video && (
            <a
              href={course.video}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "5px",
                fontSize: "12px",
                fontWeight: "600",
                color: "#38bdf8",
                textDecoration: "none",
                flexShrink: 0,
                padding: "6px 12px",
                borderRadius: "6px",
                background: "rgba(56, 189, 248, 0.08)",
                border: "1px solid rgba(56, 189, 248, 0.2)",
              }}
            >
              Watch on YouTube <ExternalLink size={13} />
            </a>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}
