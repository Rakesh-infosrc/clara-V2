import os
from google.cloud import texttospeech

def test_google_tts():
    print("🔊 Testing Google Cloud Text-to-Speech...")
    
    # Initialize the client
    try:
        client = texttospeech.TextToSpeechClient()
        print("✅ Google Cloud TTS client initialized successfully")
        
        # Set the text input to be synthesized
        synthesis_input = texttospeech.SynthesisInput(text="Hello, this is a test of Google's Text-to-Speech API.")
        
        # Build the voice request
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Neural2-F",
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )
        
        # Select the type of audio file you want returned
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        # Perform the text-to-speech request
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        
        # Save the audio to a file
        with open("test_output.mp3", "wb") as out:
            out.write(response.audio_content)
            print("✅ Test audio file created: test_output.mp3")
            print("🎤 Try playing the audio file to verify TTS is working")
            
    except Exception as e:
        print(f"❌ Error testing Google TTS: {str(e)}")
        print("Please check:")
        print("1. Your Google Cloud project has the Text-to-Speech API enabled")
        print("2. Your API key has the correct permissions")
        print("3. Your billing is set up correctly")
        print(f"4. Environment variable GOOGLE_APPLICATION_CREDENTIALS is set to: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")

if __name__ == "__main__":
    test_google_tts()
