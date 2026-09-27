# --- MAIN.PY ---
# Simple entry point (runs the UI & orchestrates threads)

import sys
import pygame
from modules import hud, audio, config


def main():
    """Main entry point - orchestrates all JARVIS components."""

    # Initialize HUD first
    hud.initialize_pygame()

    # Register state setters so audio module can update HUD
    state_setters = {
        "status": hud.update_status,
        "user_text": hud.update_user_text,
        "response": hud.update_response_text,
        "processing": audio.set_processing,  # Control is_processing flag
        "skip_audio": audio.set_skip_audio,  # Actually control mic
        "set_sleeping": audio.set_sleeping,  # Put JARVIS in sleep mode
    }
    audio.register_state_setters(state_setters)

    # Initialize audio stream and VAD
    stream = audio.start_audio_stream()

    # Main loop
    running = True
    try:
        while running:
            # Process events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break
                
                # Handle HUD interactions (Mute, Text Input)
                text_request = hud.handle_event(event)
                if text_request:
                    print(f"[UI] Text request received: {text_request}")
                    from modules.brain import ask_groq
                    import threading
                    
                    callbacks = {
                        "status": hud.update_status,
                        "user_text": hud.update_user_text,
                        "response": hud.update_response_text,
                        "processing": audio.set_processing,
                        "skip_audio": audio.set_skip_audio,
                        "set_sleeping": audio.set_sleeping,
                    }
                    hud.update_user_text(f"Paul (Text): {text_request}")
                    threading.Thread(target=ask_groq, args=(text_request, callbacks), daemon=True).start()

            # Synchronize Mute State
            audio.set_skip_audio(hud.is_muted)

            # Get current volume and render frame
            current_volume = audio.get_current_volume()
            hud.render_frame(current_volume)

    except KeyboardInterrupt:
        print("\nShutting down JARVIS...")
    except Exception as e:
        print(f"Main loop error: {e}")
    finally:
        # Cleanup
        try:
            stream.stop()
            stream.close()
        except:
            pass
        try:
            hud.cleanup()
        except:
            pass
        print("JARVIS offline.")


if __name__ == "__main__":
    main()