# --- MAIN.PY ---
# Simple entry point (runs the UI & orchestrates threads)

import sys
import threading
import pygame
from modules import hud, audio, config
from modules.proactive import ProactiveRuntime
from modules.tts import shutdown as shutdown_tts


def main():
    """Main entry point - orchestrates all JARVIS components."""
    if not config.GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is required. Add it to the project .env file before starting JARVIS."
        )

    # Initialize HUD first
    hud.initialize_pygame()

    def get_application_state():
        return {
            "busy": audio.is_processing
            or audio.current_volume > config.SILENCE_THRESHOLD,
            "sleeping": audio.is_sleeping,
            "muted": hud.is_muted,
        }

    proactive_callbacks = {
        "status": hud.update_status,
        "response": hud.update_response_text,
        "processing": audio.set_processing,
        "skip_audio": audio.set_skip_audio,
    }
    proactive_runtime = ProactiveRuntime(
        proactive_callbacks,
        get_application_state,
    )

    def update_user_text(text):
        proactive_runtime.note_user_activity()
        hud.update_user_text(text)

    # Register state setters so audio module can update HUD
    state_setters = {
        "status": hud.update_status,
        "user_text": update_user_text,
        "note_activity": proactive_runtime.note_user_activity,
        "response": hud.update_response_text,
        "processing": audio.set_processing,  # Control is_processing flag
        "skip_audio": audio.set_skip_audio,  # Actually control mic
        "set_sleeping": audio.set_sleeping,  # Put JARVIS in sleep mode
        "set_muted": hud.set_muted,
    }
    audio.register_state_setters(state_setters)

    # Initialize audio stream and VAD
    stream = audio.start_audio_stream()
    from modules.brain import client as groq_client
    from modules.worldview_research import resume_research_worker

    resume_research_worker(groq_client)
    proactive_runtime.start()

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
                    proactive_runtime.note_user_activity()
                    from modules.brain import ask_groq
                    callbacks = {
                        "status": hud.update_status,
                        "user_text": update_user_text,
                        "response": hud.update_response_text,
                        "processing": audio.set_processing,
                        "skip_audio": audio.set_skip_audio,
                        "set_sleeping": audio.set_sleeping,
                        "set_muted": hud.set_muted,
                    }
                    hud.update_user_text(f"{config.USER_NAME} (Text): {text_request}")
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
        proactive_runtime.stop()
        try:
            from modules.worldview_research import pause_research_worker
            pause_research_worker()
        except Exception as e:
            print(f"Worldview research shutdown error: {e}")
        try:
            stream.stop()
            stream.close()
        except:
            pass
        shutdown_tts()
        try:
            hud.cleanup()
        except:
            pass
        print("JARVIS offline.")


if __name__ == "__main__":
    main()