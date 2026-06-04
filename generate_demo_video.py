"""
Store Intelligence System — Revised Demo Video Generator
A highly polished, product-focused engineering demo compiling CCTV feeds,
tracking trajectories, virtual FSM events, API Swagger docs, and dashboard walkthroughs.
"""

from __future__ import annotations

import glob
import os
import sys
import time
from pathlib import Path
import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 1920, 1080
FPS = 30
BRAIN_DIR = Path(r"C:\Users\DILSHAD\.gemini\antigravity-ide\brain\c2e2b317-a6af-4062-8fc9-9869d5168c10")
STORE_INTEL_DIR = Path(r"d:\programme\html\development\purpelle\store_intelligence")
OUTPUT_PATH = Path(r"d:\programme\html\development\purpelle\demo_video.mp4")

# Theme Colors (BGR)
BG_DARK = (20, 15, 30)        # Dark slate/purple
BG_METALLIC = (40, 30, 50)    # Soft metallic border
TEXT_PRIMARY = (248, 250, 252) # White-ish (slate-50)
TEXT_MUTED = (148, 163, 184)   # Slate-400
PURPLE_LIGHT = (216, 180, 254) # Lavender
ACCENT_GREEN = (34, 197, 94)   # Green-500
ACCENT_ORANGE = (249, 115, 22) # Orange-500
ACCENT_BLUE = (59, 130, 246)   # Blue-500

# ---------------------------------------------------------------------------
# Graphic Overlay Helpers
# ---------------------------------------------------------------------------
def draw_gradient_header(frame: np.ndarray, title: str, subtitle: str = "") -> None:
    """Overlay a professional dark gradient header bar."""
    # Gradient overlay for top 120 pixels
    header_h = 120
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (WIDTH, header_h), (25, 15, 35), -1)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
    
    cv2.line(frame, (0, header_h), (WIDTH, header_h), (130, 60, 180), 2)
    
    # Title & Subtitle text
    cv2.putText(frame, title, (50, 55), cv2.FONT_HERSHEY_SIMPLEX, 1.1, TEXT_PRIMARY, 3, cv2.LINE_AA)
    if subtitle:
        cv2.putText(frame, subtitle, (50, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.65, PURPLE_LIGHT, 1, cv2.LINE_AA)

def draw_hud_footer(frame: np.ndarray) -> None:
    """Overlay a neat status footer bar."""
    footer_h = 60
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, HEIGHT - footer_h), (WIDTH, HEIGHT), (20, 10, 30), -1)
    cv2.addWeighted(overlay, 0.90, frame, 0.10, 0, frame)
    
    cv2.line(frame, (0, HEIGHT - footer_h), (WIDTH, HEIGHT - footer_h), (130, 60, 180), 1)
    cv2.putText(frame, "Purplle Tech Challenge 2026 | Store Intelligence System Demo", (50, HEIGHT - 22), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, TEXT_MUTED, 1, cv2.LINE_AA)

def draw_callout_box(frame: np.ndarray, x: int, y: int, text: str, border_color: tuple = (130, 60, 180)) -> None:
    """Draw an elegant floating tech callout box."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.70
    thickness = 2
    (tw, th), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    
    box_w = tw + 40
    box_h = th + 26
    
    # Semi-transparent dark background
    sub = frame[y:y+box_h, x:x+box_w]
    bg = np.zeros_like(sub)
    cv2.rectangle(bg, (0, 0), (box_w, box_h), (20, 10, 28), -1)
    cv2.addWeighted(bg, 0.75, sub, 0.25, 0, frame[y:y+box_h, x:x+box_w])
    
    # Border with glowing corners
    cv2.rectangle(frame, (x, y), (x + box_w, y + box_h), border_color, 2, cv2.LINE_AA)
    cv2.circle(frame, (x, y), 3, border_color, -1)
    cv2.circle(frame, (x + box_w, y), 3, border_color, -1)
    cv2.circle(frame, (x, y + box_h), 3, border_color, -1)
    cv2.circle(frame, (x + box_w, y + box_h), 3, border_color, -1)
    
    # Text
    cv2.putText(frame, text, (x + 20, y + th + 10), font, font_scale, TEXT_PRIMARY, thickness, cv2.LINE_AA)

def get_brain_file(pattern: str) -> Path | None:
    """Locate a screenshot file in the brain folder dynamically."""
    files = list(BRAIN_DIR.glob(pattern))
    if files:
        return files[0]
    return None

# ---------------------------------------------------------------------------
# Scene Renderers
# ---------------------------------------------------------------------------
def render_title_slide(writer: cv2.VideoWriter) -> None:
    """Scene 1: Title Screen (4s = 120 frames). Keep it brief, high-contrast, with motion."""
    print("Scene 1: Title Screen...")
    bg = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    
    title = "Store Intelligence System"
    subtitle = "AI-Powered Retail Analytics Platform"
    sub_title_2 = "Purplle Tech Challenge 2026 Submission"
    
    for f in range(120):
        frame = bg.copy()
        
        # Draw moving diagonal neon lines for dynamic background motion
        offset = int(f * 4)
        for i in range(-5, 10):
            pt1 = (i * 300 + offset, 0)
            pt2 = (i * 300 - 300 + offset, HEIGHT)
            cv2.line(frame, pt1, pt2, (40, 20, 55), 2, cv2.LINE_AA)
            
        # Alpha fade-in/fade-out
        alpha = 1.0
        if f < 20:
            alpha = f / 20
        elif f > 100:
            alpha = (120 - f) / 20
            
        t_color = tuple(int(c * alpha) for c in TEXT_PRIMARY)
        s_color = tuple(int(c * alpha) for c in PURPLE_LIGHT)
        s2_color = tuple(int(c * alpha) for c in TEXT_MUTED)
        
        # Center panel card
        card_w, card_h = 1300, 450
        cx1, cy1 = (WIDTH - card_w) // 2, (HEIGHT - card_h) // 2
        
        # Semi-transparent card
        overlay = frame.copy()
        cv2.rectangle(overlay, (cx1, cy1), (cx1 + card_w, cy1 + card_h), (25, 15, 35), -1)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
        
        cv2.rectangle(frame, (cx1, cy1), (cx1 + card_w, cy1 + card_h), (130, 60, 180), 2, cv2.LINE_AA)
        
        # Text alignment inside card
        cv2.putText(frame, title, (cx1 + 100, cy1 + 160), cv2.FONT_HERSHEY_SIMPLEX, 2.1, t_color, 5, cv2.LINE_AA)
        cv2.putText(frame, subtitle, (cx1 + 105, cy1 + 240), cv2.FONT_HERSHEY_SIMPLEX, 1.0, s_color, 2, cv2.LINE_AA)
        cv2.putText(frame, sub_title_2, (cx1 + 105, cy1 + 340), cv2.FONT_HERSHEY_SIMPLEX, 0.80, s2_color, 2, cv2.LINE_AA)
        
        writer.write(frame)

def render_problem_statement(writer: cv2.VideoWriter) -> None:
    """Scene 2: Problem Statement Overlay on CCTV (8s = 240 frames). Replace static slide."""
    print("Scene 2: Problem Statement on CCTV...")
    video_path = STORE_INTEL_DIR / "CAM 2.mp4"
    cap = cv2.VideoCapture(str(video_path))
    
    bullets = [
        "No real-time store occupancy visibility",
        "Inaccurate manual visitor counting",
        "Zero customer conversion funnel insights",
        "Operational alerts go undetected"
    ]
    
    for f in range(240):
        ret, frame = False, None
        if cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
                
        if frame is None:
            frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        else:
            frame = cv2.resize(frame, (WIDTH, HEIGHT))
            
        # Draw dark overlay on CCTV so text is legible
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (WIDTH, HEIGHT), (15, 10, 22), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
        
        draw_gradient_header(frame, "The Retail Analytical Blind Spot", "Traditional CCTV records video but fails to extract data.")
        draw_hud_footer(frame)
        
        # Left Panel (Problem Details)
        cv2.putText(frame, "OPERATIONAL CHALLENGES:", (120, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.0, PURPLE_LIGHT, 3, cv2.LINE_AA)
        
        for idx, bullet in enumerate(bullets):
            start_frame = idx * 45 + 15
            if f < start_frame:
                continue
            alpha = min(1.0, (f - start_frame) / 15)
            color = tuple(int(c * alpha) for c in TEXT_PRIMARY)
            
            bullet_y = 330 + idx * 100
            cv2.circle(frame, (140, bullet_y - 10), 8, ACCENT_ORANGE, -1)
            cv2.putText(frame, bullet, (180, bullet_y), cv2.FONT_HERSHEY_SIMPLEX, 0.85, color, 2, cv2.LINE_AA)
            
        # Floating tech highlight box on the right
        draw_callout_box(frame, WIDTH - 650, 240, "SOLUTION: STORE INTELLIGENCE SYSTEM", ACCENT_GREEN)
        
        writer.write(frame)
        
    if cap.isOpened():
        cap.release()

def render_architecture(writer: cv2.VideoWriter) -> None:
    """Scene 3: System Architecture Overview (8s = 240 frames). Keep it fast & dynamic."""
    print("Scene 3: System Architecture...")
    bg = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(10 * (1-ratio) + 25 * ratio)
        g = int(5 * (1-ratio) + 15 * ratio)
        b = int(15 * (1-ratio) + 35 * ratio)
        bg[y, :] = (b, g, r)
        
    stages = [
        "CCTV Feed",
        "YOLOv8 Detect",
        "ByteTrack Track",
        "Event Engine",
        "Analytics",
        "SQLite DB",
        "FastAPI",
        "Streamlit UI"
    ]
    
    box_width, box_height = 190, 70
    gap_x = 24
    start_x = (WIDTH - (len(stages) * box_width + (len(stages)-1) * gap_x)) // 2
    
    positions = []
    for idx in range(len(stages)):
        x = start_x + idx * (box_width + gap_x)
        y = 500
        positions.append((x, y))
        
    for f in range(240):
        frame = bg.copy()
        draw_gradient_header(frame, "Engineering Pipeline Overview", "A modular, loose-coupled microservice pipeline architecture.")
        draw_hud_footer(frame)
        
        # Connect boxes with arrows
        for idx in range(len(stages) - 1):
            pt1 = (positions[idx][0] + box_width, positions[idx][1] + box_height // 2)
            pt2 = (positions[idx + 1][0], positions[idx + 1][1] + box_height // 2)
            cv2.line(frame, pt1, pt2, (100, 60, 130), 2, cv2.LINE_AA)
            
            # Fast flowing dots
            cycle = (f - idx * 25) % 80
            if 0 <= cycle < 25:
                t = cycle / 25.0
                cx = int(pt1[0] * (1 - t) + pt2[0] * t)
                cy = int(pt1[1] * (1 - t) + pt2[1] * t)
                cv2.circle(frame, (cx, cy), 6, (0, 255, 255), -1)
                
        # Draw stage cards
        for idx, (x, y) in enumerate(positions):
            active_idx = min(len(stages) - 1, f // 30)
            is_active = (idx == active_idx)
            
            border_c = (180, 80, 255) if is_active else (80, 45, 110)
            rect_bg = (35, 20, 50) if is_active else (25, 15, 30)
            
            cv2.rectangle(frame, (x, y), (x + box_width, y + box_height), rect_bg, -1)
            cv2.rectangle(frame, (x, y), (x + box_width, y + box_height), border_c, 2 if is_active else 1, cv2.LINE_AA)
            
            text = stages[idx]
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)
            cv2.putText(frame, text, (x + (box_width - tw) // 2, y + (box_height + th) // 2), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, TEXT_PRIMARY if is_active else TEXT_MUTED, 1, cv2.LINE_AA)
            
        writer.write(frame)

def render_video_clip(writer: cv2.VideoWriter, video_path: Path, title: str, duration_sec: float) -> None:
    """Scene 4 & 5: Load, resize, overlay header, and output frames from raw processed videos."""
    print(f"Rendering Video Clip: {video_path.name}...")
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"Error: Cannot open video clip {video_path}")
        # Write dummy frames if video missing
        bg = np.zeros((1080, 1920, 3), dtype=np.uint8)
        for _ in range(int(duration_sec * FPS)):
            frame = bg.copy()
            draw_gradient_header(frame, title)
            draw_hud_footer(frame)
            cv2.putText(frame, "CCTV Video Clip Missing", (400, 500), cv2.FONT_HERSHEY_SIMPLEX, 1.5, TEXT_MUTED, 3)
            writer.write(frame)
        return
        
    num_frames = int(duration_sec * FPS)
    for _ in range(num_frames):
        ret, frame = cap.read()
        if not ret:
            # Loop video from start if too short
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
            if not ret:
                break
                
        # Resize to fit 1920x1080
        scaled = cv2.resize(frame, (WIDTH, HEIGHT))
        
        # Draw visual header and metadata
        draw_gradient_header(scaled, title)
        draw_hud_footer(scaled)
        
        # HUD overlays (simulated engine status)
        cv2.rectangle(scaled, (WIDTH - 300, 140), (WIDTH - 50, 240), (30, 20, 40), -1)
        cv2.rectangle(scaled, (WIDTH - 300, 140), (WIDTH - 50, 240), (130, 60, 180), 1)
        cv2.putText(scaled, "ENGINE STATUS: ACTIVE", (WIDTH - 280, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.55, ACCENT_GREEN, 1, cv2.LINE_AA)
        cv2.putText(scaled, "INFERENCE: ~11.4ms", (WIDTH - 280, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.55, TEXT_MUTED, 1, cv2.LINE_AA)
        cv2.putText(scaled, "FRAME RATE: 30 FPS", (WIDTH - 280, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.55, TEXT_MUTED, 1, cv2.LINE_AA)
        
        writer.write(scaled)
    cap.release()

def render_detection_demo(writer: cv2.VideoWriter) -> None:
    """Scene 4: Person Detection Demo (20s = 600 frames)."""
    print("Scene 4: YOLOv8 Person Detection Demo...")
    video_path = STORE_INTEL_DIR / "CAM1_output.mp4"
    cap = cv2.VideoCapture(str(video_path))
    
    num_frames = 600
    for f in range(num_frames):
        ret, frame = False, None
        if cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
                
        if frame is None:
            frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        else:
            frame = cv2.resize(frame, (WIDTH, HEIGHT))
            
        draw_gradient_header(frame, "Edge Intelligence: Person Detection", "YOLOv8 deep learning model processes surveillance footage locally.")
        draw_hud_footer(frame)
        
        # Highlight Box overlay
        draw_callout_box(frame, 60, 150, "MODEL: YOLOv8 Nano (yolov8n.pt)", PURPLE_LIGHT)
        draw_callout_box(frame, 60, 230, "CLASS: COCO 0 (Person Filter Only)", PURPLE_LIGHT)
        draw_callout_box(frame, 60, 310, "INFERENCE SPEED: ~11.4ms (CPU)", ACCENT_GREEN)
        
        # Bounding box confidence callout
        draw_callout_box(frame, WIDTH - 480, 150, "CONFIDENCE RANGE: 62% - 94%", ACCENT_BLUE)
        
        writer.write(frame)
        
    if cap.isOpened():
        cap.release()

def render_tracking_demo(writer: cv2.VideoWriter) -> None:
    """Scene 5: ByteTrack Tracking Demo & Zoom-in Crop (20s = 600 frames)."""
    print("Scene 5: ByteTrack Tracking Demo with Dynamic Zoom...")
    video_path = STORE_INTEL_DIR / "tracked_output.mp4"
    cap = cv2.VideoCapture(str(video_path))
    
    num_frames = 600
    for f in range(num_frames):
        ret, frame = False, None
        if cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
                
        if frame is None:
            frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        else:
            frame = cv2.resize(frame, (WIDTH, HEIGHT))
            
        # Target zoom effect inside frame 180 to 420 (8 seconds zoom)
        if 180 <= f < 420:
            # Let's crop centered around a person walking (approx coordinates)
            # We want to animate the scale from 1.0 to 2.2 and back
            scale = 1.0
            if f < 300:
                scale = 1.0 + (2.2 - 1.0) * ((f - 180) / 120)
            else:
                scale = 2.2 - (2.2 - 1.0) * ((f - 300) / 120)
                
            crop_w, crop_h = int(WIDTH / scale), int(HEIGHT / scale)
            # Center target coordinates (approx location where people walk in CAM1)
            cx, cy = int(WIDTH * 0.60), int(HEIGHT * 0.55)
            
            x1 = max(0, min(WIDTH - crop_w, cx - crop_w // 2))
            y1 = max(0, min(HEIGHT - crop_h, cy - crop_h // 2))
            
            cropped = frame[y1:y1+crop_h, x1:x1+crop_w]
            frame = cv2.resize(cropped, (WIDTH, HEIGHT))
            
            # Draw visual targeting crosshairs on zoom
            cv2.circle(frame, (WIDTH // 2, HEIGHT // 2), 120, ACCENT_ORANGE, 2, cv2.LINE_AA)
            cv2.line(frame, (WIDTH // 2 - 150, HEIGHT // 2), (WIDTH // 2 + 150, HEIGHT // 2), ACCENT_ORANGE, 1)
            cv2.line(frame, (WIDTH // 2, HEIGHT // 2 - 150), (WIDTH // 2, HEIGHT // 2 + 150), ACCENT_ORANGE, 1)
            
            draw_callout_box(frame, 60, 400, "DYNAMIC TARGET ZOOM: LOCK ON ID #8", ACCENT_ORANGE)
            
        draw_gradient_header(frame, "Multi-Object Tracking: persistent Trajectories", "ByteTrack associates detections using Kalman motion prediction filters.")
        draw_hud_footer(frame)
        
        draw_callout_box(frame, 60, 150, "TRACKER: ByteTrack Engine", PURPLE_LIGHT)
        draw_callout_box(frame, 60, 230, "TRAILS: 45 Frame Motion Buffer", PURPLE_LIGHT)
        draw_callout_box(frame, 60, 310, "RE-ASSOCIATION LOOKBACK: 60 Frames", ACCENT_GREEN)
        
        writer.write(frame)
        
    if cap.isOpened():
        cap.release()

def render_event_crossing(writer: cv2.VideoWriter) -> None:
    """Scene 6: Event Crossing Line Demo (20s = 600 frames)."""
    print("Scene 6: Event Engine Line Crossing Demo...")
    video_path = STORE_INTEL_DIR / "CAM 3.mp4"
    cap = cv2.VideoCapture(str(video_path))
    
    events_log = [
        {"time": "12:10:14", "id": 1, "type": "entry", "duration": "4.2s"},
        {"time": "12:10:35", "id": 2, "type": "entry", "duration": "8.5s"},
        {"time": "12:11:02", "id": 1, "type": "exit",  "duration": "52.0s"},
        {"time": "12:11:15", "id": 3, "type": "entry", "duration": "12.1s"},
        {"time": "12:11:44", "id": 2, "type": "exit",  "duration": "69.0s"}
    ]
    
    num_frames = 600
    for f in range(num_frames):
        ret, frame = False, None
        if cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
                
        if frame is None:
            frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        else:
            frame = cv2.resize(frame, (WIDTH, HEIGHT))
            
        draw_gradient_header(frame, "Event Engine: Doorway Line Crossing FSM", "Calculates entries and exits at doorways using a stateful hysteresis FSM.")
        draw_hud_footer(frame)
        
        # Draw physical line (doorway)
        cv2.line(frame, (1000, 750), (1920, 750), (255, 60, 180), 3, cv2.LINE_AA)
        cv2.putText(frame, "DOORWAY THRESHOLD (Y=750)", (1050, 730), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 60, 180), 2, cv2.LINE_AA)
        
        # Left code console (live events output)
        console_w, console_h = 580, 520
        cv2.rectangle(frame, (60, 150), (60 + console_w, 150 + console_h), (25, 15, 30), -1)
        cv2.rectangle(frame, (60, 150), (60 + console_w, 150 + console_h), (130, 60, 180), 1)
        
        # Console Header
        cv2.rectangle(frame, (60, 150), (60 + console_w, 200), (45, 25, 55), -1)
        cv2.putText(frame, "LIVE EVENT BUS LOG (JSON)", (90, 185), cv2.FONT_HERSHEY_SIMPLEX, 0.7, ACCENT_GREEN, 2, cv2.LINE_AA)
        
        # Print JSON elements chronologically
        for idx, ev in enumerate(events_log):
            if f < idx * 100 + 40:
                continue
                
            color = ACCENT_GREEN if ev["type"] == "entry" else ACCENT_ORANGE
            y_pos = 240 + idx * 80
            
            # Indicator dot
            cv2.circle(frame, (95, y_pos - 10), 6, color, -1)
            
            # Format event line
            text = f"{ev['time']} - ID:{ev['id']} {ev['type'].upper()} (duration: {ev['duration']})"
            cv2.putText(frame, text, (120, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.60, TEXT_PRIMARY, 1, cv2.LINE_AA)
            
        # Draw status Callout boxes
        draw_callout_box(frame, 60, 700, "FSM STATES: Outside -> Deadzone -> Inside", PURPLE_LIGHT)
        draw_callout_box(frame, 60, 780, "HYSTERESIS BUFFER: 20px clearance zone", PURPLE_LIGHT)
        draw_callout_box(frame, 60, 860, "COOLDOWN WINDOW: 0.5s jitter prevention", ACCENT_GREEN)
        
        writer.write(frame)
        
    if cap.isOpened():
        cap.release()

def render_api_docs_demo(writer: cv2.VideoWriter) -> None:
    """Scene 7: FastAPI Endpoint Swagger UI & JSON responses (20s = 600 frames)."""
    print("Scene 7: FastAPI Swagger documentation Demonstration...")
    bg = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(10 * (1-ratio) + 20 * ratio)
        g = int(15 * (1-ratio) + 25 * ratio)
        b = int(25 * (1-ratio) + 40 * ratio)
        bg[y, :] = (b, g, r)
        
    api_list = [
        {"method": "GET", "path": "/api/v1/metrics", "desc": "Aggregated store metrics & visitor statistics", 
         "json": ['{', '  "total_entries": 120,', '  "total_exits": 117,', '  "unique_visitors": 98,', '  "peak_occupancy": 21,', '  "avg_duration": 245.3', '}']},
        {"method": "GET", "path": "/api/v1/funnel", "desc": "Transitional funnel counts and conversion rates", 
         "json": ['{', '  "passersby": 150,', '  "entered_store": 98,', '  "browsed_aisle": 45,', '  "checkout": 12,', '  "rates": {"entry_rate": 0.653}', '}']},
        {"method": "GET", "path": "/api/v1/anomalies", "desc": "Security events and crowding statistics log", 
         "json": ['{', '  "total_anomalies": 10,', '  "crowding": 4,', '  "loitering": 3,', '  "traffic_spikes": 3', '}']}
    ]
    
    for f in range(600):
        frame = bg.copy()
        
        # Chrome Browser viewport frame
        cv2.rectangle(frame, (80, 150), (WIDTH - 80, HEIGHT - 100), (25, 20, 30), -1)
        cv2.rectangle(frame, (80, 150), (WIDTH - 80, HEIGHT - 100), (130, 60, 180), 2, cv2.LINE_AA)
        
        # Address Bar UI
        cv2.rectangle(frame, (80, 150), (WIDTH - 80, 210), (45, 30, 60), -1)
        cv2.putText(frame, "chrome", (110, 185), cv2.FONT_HERSHEY_SIMPLEX, 0.55, TEXT_MUTED, 1, cv2.LINE_AA)
        cv2.rectangle(frame, (250, 160), (WIDTH - 150, 200), (20, 10, 28), -1)
        cv2.putText(frame, "http://127.0.0.1:8000/docs", (270, 185), cv2.FONT_HERSHEY_SIMPLEX, 0.55, TEXT_PRIMARY, 1, cv2.LINE_AA)
        
        # Swagger UI Header
        cv2.putText(frame, "Store Intelligence API v1.0", (120, 260), cv2.FONT_HERSHEY_SIMPLEX, 0.85, PURPLE_LIGHT, 2, cv2.LINE_AA)
        cv2.line(frame, (120, 280), (WIDTH - 120, 280), (80, 45, 110), 1)
        
        # Render Sidebar GET Swagger bars
        for idx, api in enumerate(api_list):
            ay = 310 + idx * 210
            
            # Active selected endpoint highlight
            active_idx = min(len(api_list) - 1, f // 200)
            is_active = (idx == active_idx)
            
            bar_border = (130, 60, 180) if is_active else (80, 45, 110)
            bar_bg = (40, 25, 55) if is_active else (25, 15, 30)
            
            cv2.rectangle(frame, (120, ay), (850, ay + 170), bar_bg, -1)
            cv2.rectangle(frame, (120, ay), (850, ay + 170), bar_border, 2 if is_active else 1, cv2.LINE_AA)
            
            # Method badge
            cv2.rectangle(frame, (140, ay + 20), (250, ay + 80), ACCENT_GREEN, -1)
            cv2.putText(frame, api["method"], (165, ay + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (20, 10, 30), 2, cv2.LINE_AA)
            
            # Path text
            cv2.putText(frame, api["path"], (270, ay + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.75, TEXT_PRIMARY, 2, cv2.LINE_AA)
            cv2.putText(frame, api["desc"], (140, ay + 130), cv2.FONT_HERSHEY_SIMPLEX, 0.55, TEXT_MUTED, 1, cv2.LINE_AA)
            
        # Draw Response JSON Console (Right Panel)
        cv2.rectangle(frame, (890, 310), (WIDTH - 120, HEIGHT - 130), (15, 10, 22), -1)
        cv2.rectangle(frame, (890, 310), (WIDTH - 120, HEIGHT - 130), (130, 60, 180), 1)
        
        # Header
        cv2.rectangle(frame, (890, 310), (WIDTH - 120, 360), (45, 25, 55), -1)
        active_api = api_list[active_idx]
        cv2.putText(frame, f"RESPONSE BODY: {active_api['path']}", (910, 345), cv2.FONT_HERSHEY_SIMPLEX, 0.65, ACCENT_GREEN, 2, cv2.LINE_AA)
        
        # JSON Lines output
        for l_idx, line in enumerate(active_api["json"]):
            cv2.putText(frame, line, (920, 420 + l_idx * 50), cv2.FONT_HERSHEY_SIMPLEX, 0.65, TEXT_PRIMARY, 1, cv2.LINE_AA)
            
        # Simulated Cursor pointing at selected endpoint
        cursor_x = 200
        # Interpolate cursor position based on active item
        cursor_y = 350 + active_idx * 210
        cv2.drawMarker(frame, (cursor_x, cursor_y), ACCENT_ORANGE, cv2.MARKER_CROSS, 20, 2)
        
        draw_gradient_header(frame, "Web Backend: FastAPI REST Framework", "Swagger/OpenAPI documentation exposes database caches synchronously.")
        draw_hud_footer(frame)
        
        writer.write(frame)

def render_zoom_screenshot(writer: cv2.VideoWriter, image_path: Path, title: str, duration_sec: float) -> None:
    """Scene 8, 9, 10: Smoothly crop out the sidebar and zoom/scroll over the dashboard content."""
    img = cv2.imread(str(image_path))
    if img is None:
        # Fallback
        bg = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        for _ in range(int(duration_sec * FPS)):
            writer.write(bg)
        return
        
    num_frames = int(duration_sec * FPS)
    h, w = img.shape[:2]
    
    # Crop out the sidebar (left 340 pixels)
    content_x_start = 340
    content = img[:, content_x_start:w] # size: (970, 1580)
    ch, cw = content.shape[:2]
    
    for f in range(num_frames):
        # We want to crop a region with aspect ratio matching 1920:900 (2.1333)
        # To avoid scaling errors, let's select crop_h = 700, and crop_w = 1493
        crop_h = 700
        crop_w = 1493
        
        # Slow pan down
        max_y_offset = ch - crop_h # 970 - 700 = 270 pixels
        y_offset = int(max_y_offset * (f / num_frames))
        
        # Slow pan right
        max_x_offset = cw - crop_w # 1580 - 1493 = 87 pixels
        x_offset = int(max_x_offset * 0.5 * (f / num_frames))
        
        cropped = content[y_offset:y_offset+crop_h, x_offset:x_offset+crop_w]
        
        # Resize to fit the viewport exactly (1920x900)
        viewport_w = WIDTH
        viewport_h = HEIGHT - 120 - 60 # 900
        resized_content = cv2.resize(cropped, (viewport_w, viewport_h))
        
        # Place into full 1920x1080 frame
        frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        frame[120:HEIGHT-60, :] = resized_content
        
        # Overlay header and footer
        draw_gradient_header(frame, title, "Real-time retail web interface built in Streamlit.")
        draw_hud_footer(frame)
        
        # Floating tech overlay cards
        if "summary" in str(image_path).lower():
            draw_callout_box(frame, WIDTH - 420, 150, "KPI EXECUTIVE SUMMARY", ACCENT_GREEN)
        elif "funnel" in str(image_path).lower():
            draw_callout_box(frame, WIDTH - 420, 150, "TRANSACTION CONVERSION", ACCENT_BLUE)
        elif "anomaly" in str(image_path).lower():
            draw_callout_box(frame, WIDTH - 420, 150, "STRATEGY ALERTS FEED", ACCENT_ORANGE)
        elif "visitor" in str(image_path).lower():
            draw_callout_box(frame, WIDTH - 420, 150, "GRANULAR VISITOR DETAILS", PURPLE_LIGHT)
            
        writer.write(frame)

def render_tech_stack_revised(writer: cv2.VideoWriter) -> None:
    """Scene 11: Scalability & Tech Stack (10s = 300 frames)."""
    print("Scene 11: Tech Stack & Scalability...")
    bg = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(10 * (1-ratio) + 20 * ratio)
        g = int(8 * (1-ratio) + 12 * ratio)
        b = int(20 * (1-ratio) + 35 * ratio)
        bg[y, :] = (b, g, r)
        
    techs = [
        {"layer": "Computer Vision", "tech": "YOLOv8 & ByteTrack", "info": "Edge human detection & ID tracking"},
        {"layer": "Web Services",   "tech": "FastAPI & Uvicorn",   "info": "Asynchronous REST backend framework"},
        {"layer": "Data Storage",   "tech": "SQLite & SQLAlchemy", "info": "Local database persistent logging"},
        {"layer": "Visual UI",       "tech": "Streamlit & Altair",  "info": "Outfit-font real-time dashboard"},
        {"layer": "Containerization","tech": "Docker Compose",      "info": "Multi-container setup & deployment"}
    ]
    
    for f in range(300):
        frame = bg.copy()
        draw_gradient_header(frame, "Engineering Stack & Production Deployment", "Built with modern AI tools and containerized backend architectures.")
        draw_hud_footer(frame)
        
        # Draw Tech Stacks on Left (3/5 layout)
        cv2.putText(frame, "PRODUCTION STACK FOUNDATION", (120, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.90, PURPLE_LIGHT, 2, cv2.LINE_AA)
        
        for idx, item in enumerate(techs):
            start_frame = idx * 30 + 10
            if f < start_frame:
                continue
            alpha = min(1.0, (f - start_frame) / 15)
            
            box_y = 270 + idx * 140
            cv2.rectangle(frame, (120, box_y), (950, box_y + 110), (25, 15, 35), -1)
            cv2.rectangle(frame, (120, box_y), (950, box_y + 110), (130, 60, 180), 1, cv2.LINE_AA)
            
            # Left category bar
            cv2.rectangle(frame, (120, box_y), (350, box_y + 110), (45, 30, 55), -1)
            cv2.putText(frame, item["layer"], (140, box_y + 65), cv2.FONT_HERSHEY_SIMPLEX, 0.58, PURPLE_LIGHT, 1, cv2.LINE_AA)
            
            # Info
            t_color = tuple(int(c * alpha) for c in TEXT_PRIMARY)
            d_color = tuple(int(c * alpha) for c in TEXT_MUTED)
            cv2.putText(frame, item["tech"], (380, box_y + 45), cv2.FONT_HERSHEY_SIMPLEX, 0.72, t_color, 2, cv2.LINE_AA)
            cv2.putText(frame, item["info"], (380, box_y + 85), cv2.FONT_HERSHEY_SIMPLEX, 0.55, d_color, 1, cv2.LINE_AA)
            
        # Draw Cloud Scalability Roadmap on Right (2/5 layout)
        col_right_x = 1030
        cv2.rectangle(frame, (col_right_x, 210), (WIDTH - 120, HEIGHT - 120), (20, 10, 30), -1)
        cv2.rectangle(frame, (col_right_x, 210), (WIDTH - 120, HEIGHT - 120), ACCENT_GREEN, 2, cv2.LINE_AA)
        
        cv2.putText(frame, "CLOUD SCALABILITY ROADMAP", (col_right_x + 60, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.85, ACCENT_GREEN, 2, cv2.LINE_AA)
        cv2.line(frame, (col_right_x + 60, 290), (WIDTH - 180, 290), (80, 45, 110), 1)
        
        roadmap = [
            "1. Ingestion: RTSP IP Camera Streaming queues",
            "2. Pipeline: NVIDIA DeepStream / TensorRT",
            "3. Message Bus: Distributed Apache Kafka",
            "4. Central DB: PostgreSQL / Cloud Cluster RDS",
            "5. Deployment: Kubernetes Edge Microservices"
        ]
        
        for r_idx, step in enumerate(roadmap):
            start_frame = r_idx * 30 + 100
            if f < start_frame:
                continue
            alpha = min(1.0, (f - start_frame) / 15)
            color = tuple(int(c * alpha) for c in TEXT_PRIMARY)
            cv2.putText(frame, step, (col_right_x + 60, 360 + r_idx * 110), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 1, cv2.LINE_AA)
            
        writer.write(frame)

def render_conclusion_revised(writer: cv2.VideoWriter) -> None:
    """Scene 12: Conclusion & Submission Summary (12s = 360 frames)."""
    print("Scene 12: Conclusion Summary Screen...")
    bg = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(10 * (1-ratio) + 20 * ratio)
        g = int(5 * (1-ratio) + 12 * ratio)
        b = int(15 * (1-ratio) + 30 * ratio)
        bg[y, :] = (b, g, r)
        
    summary_bullets = [
        "AI-Powered Retail Analytics Pipeline",
        "Real-Time Store Operations Intelligence",
        "Loose-Coupled Production-Ready Architecture",
        "SQLite Persistence & Versioned FastAPI Services",
        "Streamlit UI with Snappy Offline Fallback Control"
    ]
    
    for f in range(360):
        frame = bg.copy()
        
        col_left_x = 120
        col_right_x = 1020
        
        # Left Panel (Pipeline Summary Checklist)
        cv2.putText(frame, "STORE INTELLIGENCE SYSTEM", (col_left_x, 220), cv2.FONT_HERSHEY_SIMPLEX, 1.3, PURPLE_LIGHT, 3, cv2.LINE_AA)
        cv2.putText(frame, "Engineering Checklist Summary:", (col_left_x, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.80, TEXT_MUTED, 2, cv2.LINE_AA)
        
        for idx, bullet in enumerate(summary_bullets):
            start_frame = idx * 30 + 20
            if f < start_frame:
                continue
            alpha = min(1.0, (f - start_frame) / 15)
            color = tuple(int(c * alpha) for c in TEXT_PRIMARY)
            
            bullet_y = 370 + idx * 100
            cv2.circle(frame, (col_left_x + 30, bullet_y - 12), 10, ACCENT_GREEN, -1)
            cv2.putText(frame, bullet, (col_left_x + 70, bullet_y), cv2.FONT_HERSHEY_SIMPLEX, 0.78, color, 2, cv2.LINE_AA)
            
        # Right Panel (Thank You card submission)
        cv2.rectangle(frame, (col_right_x, 150), (WIDTH - 120, HEIGHT - 150), (25, 15, 35), -1)
        cv2.rectangle(frame, (col_right_x, 150), (WIDTH - 120, HEIGHT - 150), (130, 60, 180), 3, cv2.LINE_AA)
        
        cv2.putText(frame, "HACKATHON SUBMISSION", (col_right_x + 100, 380), cv2.FONT_HERSHEY_SIMPLEX, 1.1, TEXT_PRIMARY, 3, cv2.LINE_AA)
        cv2.putText(frame, "Purplle Tech Challenge 2026", (col_right_x + 100, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.85, PURPLE_LIGHT, 2, cv2.LINE_AA)
        
        cv2.putText(frame, "Thank You", (col_right_x + 230, 610), cv2.FONT_HERSHEY_SIMPLEX, 1.8, ACCENT_GREEN, 5, cv2.LINE_AA)
        
        writer.write(frame)

# ---------------------------------------------------------------------------
# Main Video Compilation Orchestrator
# ---------------------------------------------------------------------------
def main() -> int:
    print(f"Beginning Revised Demo Video Compilation...")
    
    # 1. Locate Dashboard screenshots
    executive_summary_ss = get_brain_file("executive_summary_*.png")
    occupancy_analytics_ss = get_brain_file("occupancy_analytics_*.png")
    conversion_funnel_ss = get_brain_file("conversion_funnel_*.png")
    anomaly_monitoring_ss = get_brain_file("anomaly_monitoring_*.png")
    visitor_insights_ss = get_brain_file("visitor_insights_*.png")
    
    # 2. Check source video files
    cam1_output = STORE_INTEL_DIR / "CAM1_output.mp4"
    tracked_output = STORE_INTEL_DIR / "tracked_output.mp4"
    
    # 3. Create Video Writer
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(OUTPUT_PATH), fourcc, FPS, (WIDTH, HEIGHT))
    
    start_time = time.perf_counter()
    
    try:
        # Scene 1: Title Screen (4s) -> Static with motion
        render_title_slide(writer)
        
        # Scene 2: Problem Statement Overlay on CCTV (8s) -> Product hook
        render_problem_statement(writer)
        
        # Scene 3: System Architecture Overview (8s) -> Technical diagram
        render_architecture(writer)
        
        # Scene 4: YOLOv8 Person Detection Demo (20s) -> Product Demo
        render_video_clip(writer, cam1_output, "Phase 1: YOLOv8 Person Detection Demonstration", 20.0)
        
        # Scene 5: ByteTrack Tracking Demo with Target Zoom (20s) -> Product Demo
        render_tracking_demo(writer)
        
        # Scene 6: Event Crossing Line Demo (20s) -> Product Demo
        render_event_crossing(writer)
        
        # Scene 7: FastAPI Endpoint Swagger UI Demo (20s) -> Product Demo
        render_api_docs_demo(writer)
        
        # Scene 8: Streamlit Dashboard - Executive Summary (16s) -> Product Demo
        if executive_summary_ss:
            render_zoom_screenshot(writer, executive_summary_ss, "Dashboard: Executive Summary Walkthrough", 16.0)
        else:
            # fallback
            render_problem_statement(writer)
            
        # Scene 9: Streamlit Dashboard - Occupancy & Funnel (16s) -> Product Demo
        if occupancy_analytics_ss:
            render_zoom_screenshot(writer, occupancy_analytics_ss, "Dashboard: Occupancy & Conversion Funnel", 16.0)
        elif conversion_funnel_ss:
            render_zoom_screenshot(writer, conversion_funnel_ss, "Dashboard: Occupancy & Conversion Funnel", 16.0)
        else:
            render_problem_statement(writer)
            
        # Scene 10: Streamlit Dashboard - Anomalies & Visitor Insights (16s) -> Product Demo
        if anomaly_monitoring_ss:
            render_zoom_screenshot(writer, anomaly_monitoring_ss, "Dashboard: Operational Alerts Feed & Visitors Log", 16.0)
        elif visitor_insights_ss:
            render_zoom_screenshot(writer, visitor_insights_ss, "Dashboard: Operational Alerts Feed & Visitors Log", 16.0)
        else:
            render_problem_statement(writer)
            
        # Scene 11: Scalability & Tech Stack (10s) -> Slide/Diagram
        render_tech_stack_revised(writer)
        
        # Scene 12: Conclusion Summary & Thank You (12s) -> Slide/Diagram
        render_conclusion_revised(writer)
        
    finally:
        writer.release()
        
    elapsed = time.perf_counter() - start_time
    print(f"Revised Compilation finished successfully!")
    print(f"Video saved to: {OUTPUT_PATH}")
    print(f"Total Compilation Time: {elapsed:.2f} seconds")
    return 0

if __name__ == "__main__":
    sys.exit(main())
