import sys
import time
import threading
import numpy as np
import pygame
from pynput import keyboard
import tkinter as tk
from tkinter import messagebox
import wave
import os

# --- Audio Initialization ---
pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.mixer.init()
fs = 44100  # Sampling frequency

# --- Global State ---
base_octave = 4
octave = base_octave
recording = False
recorded_notes = []
sustain_mode = True
volume = 0.5
playing_notes = {}
active_threads = []
recorded_audio = []

# --- Note Mapping ---
white_keys = ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k']
white_notes = ['C', 'D', 'E', 'F', 'G', 'A', 'B', 'C+']
black_keys = ['w', 'e', '', 't', 'y', 'u', '', '']
black_notes = ['C#', 'D#', '', 'F#', 'G#', 'A#', '', '']
note_freqs = {
    'C': 261.63,  'C#': 277.18,
    'D': 293.66,  'D#': 311.13,
    'E': 329.63,
    'F': 349.23,  'F#': 369.99,
    'G': 392.00,  'G#': 415.30,
    'A': 440.00,  'A#': 466.16,
    'B': 493.88,
    'C+': 523.25
}

key_note_map = {}
for k, n in zip(white_keys, white_notes):
    key_note_map[k] = n
for k, n in zip(black_keys, black_notes):
    if k:
        key_note_map[k] = n

# --- Sound Generation ---
def get_freq(note, octave_shift=0):
    """Calculate frequency for a note with octave shift."""
    base_freq = note_freqs[note]
    return base_freq * (2 ** octave_shift)

def generate_tone(freq, duration=0.5):
    """Generate a sine wave tone for the given frequency and duration."""
    t = np.linspace(0, duration, int(fs * duration), False)
    wave_data = np.sin(freq * t * 2 * np.pi)
    wave_data *= (2**15 - 1) / np.max(np.abs(wave_data))
    return wave_data.astype(np.int16)

def play_note(note, octv, duration=5):
    """Play a piano note with the given octave and duration."""
    freq = get_freq(note, octv - base_octave)
    audio = generate_tone(freq, duration)
    sound = pygame.mixer.Sound(buffer=audio)
    sound.set_volume(volume)
    sound.play(-1 if sustain_mode else 0)
    if recording:
        recorded_notes.append((note, octv, time.time()))
        recorded_audio.append(audio)
    return sound

# --- GUI Event Handlers ---
def change_octave(direction):
    global octave
    octave = max(2, min(6, octave + direction))
    octave_display.set(f"Octave: {octave}")

def toggle_recording():
    global recording
    recording = not recording
    recorded_notes.clear()
    recorded_audio.clear()
    record_status.set(f"Recording: {'ON' if recording else 'OFF'}")
    print("🔴 Recording..." if recording else "🟢 Stopped.")

def toggle_sustain():
    global sustain_mode
    sustain_mode = not sustain_mode
    sustain_status.set(f"Sustain: {'ON' if sustain_mode else 'OFF'}")
    print(f"Sustain mode {'ON' if sustain_mode else 'OFF'}")

def update_note_display():
    notes = [key_note_map[k] + str(octave) for k in playing_notes]
    note_display.set("Playing: " + (", ".join(notes) if notes else "None"))

def highlight_key(char, active=True):
    if char in labels:
        if char in black_keys:
            color = "lightgreen" if active else "black"
        else:
            color = "lightgreen" if active else "white"
        labels[char]["canvas"].itemconfig(labels[char]["key_id"], fill=color)

def key_event(char):
    if char in key_note_map and char not in playing_notes:
        note = key_note_map[char]
        sound = play_note(note, octave)
        playing_notes[char] = sound
        highlight_key(char, True)
        update_note_display()

def stop_key(char):
    if char in playing_notes:
        playing_notes[char].stop()
        del playing_notes[char]
        highlight_key(char, False)
        update_note_display()

def playback():
    if not recorded_notes:
        print("No notes recorded.")
        messagebox.showinfo("Playback", "No notes recorded.")
        return
    
    base_time = recorded_notes[0][2]
    prev_time = base_time
    
    for note, octv, tstamp in recorded_notes:
        delay = tstamp - prev_time
        if delay > 0:
            time.sleep(delay)
        play_note(note, octv, duration=0.5)
        prev_time = tstamp

def export_wav():
    if not recorded_audio:
        messagebox.showinfo("Export", "No recording to export.")
        return
    
    final = np.concatenate(recorded_audio)
    filepath = "piano_recording.wav"
    
    with wave.open(filepath, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(fs)
        f.writeframes(final.tobytes())
    
    messagebox.showinfo("Export", f"Saved to {os.path.abspath(filepath)}")

def on_press(key):
    global octave, recording, sustain_mode, volume
    try:
        char = key.char.lower()
        if char == 'z':
            change_octave(-1)
        elif char == 'x':
            change_octave(1)
        elif char == 'r':
            toggle_recording()
        elif char == 'p':
            print("▶️ Playback...")
            threading.Thread(target=playback).start()
        elif char == 'm':
            toggle_sustain()
        elif char == 'v':
            export_wav()
        elif char in key_note_map:
            key_event(char)
    except AttributeError:
        if key == keyboard.Key.esc:
            root.destroy()
            return False
        elif key == keyboard.Key.up:
            volume = min(1.0, volume + 0.1)
            volume_display.set(f"Volume: {int(volume*100)}%")
            print(f"🔊 Volume: {int(volume*100)}%")
        elif key == keyboard.Key.down:
            volume = max(0.0, volume - 0.1)
            volume_display.set(f"Volume: {int(volume*100)}%")
            print(f"🔉 Volume: {int(volume*100)}%")

def on_release(key):
    try:
        char = key.char.lower()
        if not sustain_mode:
            stop_key(char)
    except AttributeError:
        pass

# --- GUI Setup ---
root = tk.Tk()
root.title("🎹 Advanced Piano")
root.geometry("800x400")  # Taller window for more space
root.configure(bg="#f0f0f0")  # Light background color

# Create frames for better organization
control_frame = tk.Frame(root, bg="#f0f0f0", pady=10)
control_frame.pack(fill="x")

# Add control buttons (using pack instead of grid)
btn_frame = tk.Frame(control_frame, bg="#f0f0f0")
btn_frame.pack()

tk.Button(btn_frame, text="Octave ▼", command=lambda: change_octave(-1), 
          bg="#e0e0e0", fg="#000000", width=10).pack(side=tk.LEFT, padx=5)
tk.Button(btn_frame, text="Octave ▲", command=lambda: change_octave(1), 
          bg="#e0e0e0", fg="#000000", width=10).pack(side=tk.LEFT, padx=5)
tk.Button(btn_frame, text="🔴 Record", command=toggle_recording, 
          bg="#ff6666", fg="#ffffff", width=10).pack(side=tk.LEFT, padx=5)
tk.Button(btn_frame, text="▶️ Play", command=lambda: threading.Thread(target=playback).start(), 
          bg="#66cc66", fg="#ffffff", width=10).pack(side=tk.LEFT, padx=5)
tk.Button(btn_frame, text="💾 Export", command=export_wav, 
          bg="#6699cc", fg="#ffffff", width=10).pack(side=tk.LEFT, padx=5)
tk.Button(btn_frame, text="Sustain", command=toggle_sustain, 
          bg="#e0e0e0", fg="#000000", width=10).pack(side=tk.LEFT, padx=5)

# Status indicators
status_frame = tk.Frame(root, bg="#f0f0f0", pady=5)
status_frame.pack(fill="x")

# Status displays
note_display = tk.StringVar(value="Ready to play")
octave_display = tk.StringVar(value=f"Octave: {octave}")
record_status = tk.StringVar(value="Recording: OFF")
sustain_status = tk.StringVar(value="Sustain: ON")
volume_display = tk.StringVar(value=f"Volume: {int(volume*100)}%")

tk.Label(status_frame, textvariable=note_display, font=("Arial", 14), fg="blue", bg="#f0f0f0").pack()

status_bar = tk.Frame(status_frame, bg="#f0f0f0")
status_bar.pack(pady=5)

tk.Label(status_bar, textvariable=octave_display, font=("Arial", 12), fg="#333333", bg="#f0f0f0").pack(side=tk.LEFT, padx=10)
tk.Label(status_bar, textvariable=record_status, font=("Arial", 12), fg="#cc3333", bg="#f0f0f0").pack(side=tk.LEFT, padx=10)
tk.Label(status_bar, textvariable=sustain_status, font=("Arial", 12), fg="#333333", bg="#f0f0f0").pack(side=tk.LEFT, padx=10)
tk.Label(status_bar, textvariable=volume_display, font=("Arial", 12), fg="#333333", bg="#f0f0f0").pack(side=tk.LEFT, padx=10)

# Piano keyboard container
keyboard_frame = tk.Frame(root, bg="#f0f0f0", pady=10)
keyboard_frame.pack(fill="x")

piano_container = tk.Frame(keyboard_frame, bg="#444444", padx=5, pady=5)
piano_container.pack()

# --- Keyboard Layout ---
# White keys
white_key_width = 60
white_key_height = 180
black_key_width = 40
black_key_height = 110
piano_canvas = tk.Canvas(piano_container, width=white_key_width*len(white_keys), height=white_key_height+20, 
                         bg="#444444", highlightthickness=0)
piano_canvas.pack()

labels = {}

# Draw white keys
for i, key in enumerate(white_keys):
    x = i * white_key_width
    key_id = piano_canvas.create_rectangle(x, 0, x+white_key_width, white_key_height, 
                                          fill="white", outline="black", width=1, tags=f"key_{key}")
    text_id = piano_canvas.create_text(x+white_key_width/2, white_key_height-20, 
                                      text=key.upper(), font=("Arial", 14), tags=f"text_{key}")
    note_id = piano_canvas.create_text(x+white_key_width/2, white_key_height-40, 
                                       text=white_notes[i], font=("Arial", 12), fill="gray", tags=f"note_{key}")
    
    # Bind events to the key
    piano_canvas.tag_bind(f"key_{key}", "<Button-1>", lambda e, k=key: key_event(k))
    piano_canvas.tag_bind(f"text_{key}", "<Button-1>", lambda e, k=key: key_event(k))
    piano_canvas.tag_bind(f"note_{key}", "<Button-1>", lambda e, k=key: key_event(k))
    
    labels[key] = {"canvas": piano_canvas, "key_id": key_id}

# Draw black keys
for i, key in enumerate(black_keys):
    if key:
        x = i * white_key_width + (white_key_width * 3/4)
        key_id = piano_canvas.create_rectangle(x, 0, x+black_key_width, black_key_height, 
                                              fill="black", outline="black", width=1, tags=f"key_{key}")
        text_id = piano_canvas.create_text(x+black_key_width/2, black_key_height-20, 
                                          text=key.upper(), font=("Arial", 12), fill="white", tags=f"text_{key}")
        note_id = piano_canvas.create_text(x+black_key_width/2, black_key_height-40, 
                                          text=black_notes[i], font=("Arial", 10), fill="lightgray", tags=f"note_{key}")
        
        # Bind events to the key
        piano_canvas.tag_bind(f"key_{key}", "<Button-1>", lambda e, k=key: key_event(k))
        piano_canvas.tag_bind(f"text_{key}", "<Button-1>", lambda e, k=key: key_event(k))
        piano_canvas.tag_bind(f"note_{key}", "<Button-1>", lambda e, k=key: key_event(k))
        
        labels[key] = {"canvas": piano_canvas, "key_id": key_id}

# Add mouse release handler for when clicking piano keys
piano_canvas.bind("<ButtonRelease-1>", lambda e: None)  # Placeholder for future mouse release handling

# --- Start Listener ---
listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

# --- Instructions ---
print("""
🎹 Piano Ready!
Keys:
- A–K for white notes
- W, E, T, Y, U for black notes
- Z / X: Octave Down/Up
- R: Start/Stop Recording
- P: Playback
- V: Export Recording to WAV
- M: Toggle Sustain
- ↑ / ↓: Volume
- ESC: Quit
You can also click the keys with your mouse.
""")

# --- Run GUI ---
root.mainloop()
