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
  const startSec = existingProgress?.progressSeconds || 0;
  
  const iframeRef = useRef(null);
  const playerRef = useRef(null);

  // Initial position from existing progress
  const [currentSeconds, setCurrentSeconds] = useState(startSec);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isCompleted, setIsCompleted] = useState(
    existingProgress?.isCompleted || (existingProgress?.progressPercentage >= 90) || false
  );
  const [iframeLoaded, setIframeLoaded] = useState(false);

  // Keep ref for current values to save on unmount/close
  const progressRef = useRef({ currentSeconds, totalDurationSeconds, isCompleted });

  useEffect(() => {
    if (course) {
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.body.style.overflow = "unset";
    };
  }, [course]);

  // Load YouTube Iframe API if not loaded
  useEffect(() => {
    if (!window.YT) {
      const tag = document.createElement("script");
      tag.src = "https://www.youtube.com/iframe_api";
      const firstScriptTag = document.getElementsByTagName("script")[0];
      if (firstScriptTag && firstScriptTag.parentNode) {
        firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
      } else {
        document.head.appendChild(tag);
      }
    }
  }, []);

  // Initialize YT Player once the iframe has loaded
  useEffect(() => {
    if (!iframeLoaded) return;

    let player;
    let timeInterval;

    const onPlayerReady = (event) => {
      playerRef.current = event.target;
      if (startSec > 0) {
        event.target.seekTo(startSec, true);
      }
    };

    const onPlayerStateChange = (event) => {
      const state = event.data;
      if (state === window.YT.PlayerState.PLAYING) {
        setIsPlaying(true);
        startTimeTracking();
      } else if (state === window.YT.PlayerState.PAUSED) {
        setIsPlaying(false);
        stopTimeTracking();
      } else if (state === window.YT.PlayerState.ENDED) {
        setIsPlaying(false);
        stopTimeTracking();
        
        const duration = event.target.getDuration() || totalDurationSeconds;
        setCurrentSeconds(duration);
        setIsCompleted(true);
        progressRef.current = {
          currentSeconds: duration,
          totalDurationSeconds: duration,
          isCompleted: true,
          pct: 100,
        };
        if (onSaveProgress && course) {
          onSaveProgress(course.id, duration, duration, 100, true);
        }
      }
    };

    const initPlayer = () => {
      if (!iframeRef.current) return;
      player = new window.YT.Player(iframeRef.current, {
        events: {
          onReady: onPlayerReady,
          onStateChange: onPlayerStateChange,
        },
      });
    };

    const startTimeTracking = () => {
      if (timeInterval) clearInterval(timeInterval);
      timeInterval = setInterval(() => {
        if (player && player.getCurrentTime) {
          const time = Math.round(player.getCurrentTime());
          const duration = player.getDuration() || totalDurationSeconds;
          setCurrentSeconds(time);

          const nextPct = Math.round((time / duration) * 100);
          if (nextPct >= 90) {
            setIsCompleted(true);
          }

          progressRef.current = {
            currentSeconds: time,
            totalDurationSeconds: duration,
            isCompleted: isCompleted || nextPct >= 90,
            pct: nextPct,
          };
        }
      }, 500);
    };

    const stopTimeTracking = () => {
      if (timeInterval) {
        clearInterval(timeInterval);
        timeInterval = null;
      }
    };

    if (window.YT && window.YT.Player) {
      initPlayer();
    } else {
      const prevCallback = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = () => {
        if (prevCallback) prevCallback();
        initPlayer();
      };
    }

    return () => {
      stopTimeTracking();
      if (player && player.destroy) {
        player.destroy();
      }
    };
  }, [iframeLoaded, course, startSec, totalDurationSeconds, isCompleted, onSaveProgress]);

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
  // Clean up duplicate query parameters using getEmbedSrc helper
  const getEmbedSrc = () => {
    let url = course.embedUrl || (course.videoId ? `https://www.youtube.com/embed/${course.videoId}` : "");
    if (!url) return "";
    if (!url.includes("?")) {
      url += "?autoplay=1&cc_load_policy=1";
    }
    if (!url.includes("enablejsapi=1")) {
      url += "&enablejsapi=1";
    }
    if (startSec > 0 && !url.includes("start=")) {
      url += `&start=${startSec}`;
    }
    return url;
  };
  const embedSrc = getEmbedSrc();

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
            id={`yt-player-${course.id}`}
            ref={iframeRef}
            src={embedSrc}
            onLoad={() => setIframeLoaded(true)}
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
            background: "rgba(18, 24, 38, 0.95)",
            borderTop: "1px solid rgba(255, 255, 255, 0.08)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
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
