"""
Gemini AI integration for advanced phishing detection
"""
import os
import requests
import json
import time
from datetime import datetime
import threading
import queue
import re

class GeminiAnalyzer:
    """Integrate Gemini API for advanced email analysis"""

    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError(
                "No Gemini API key provided. Set the GEMINI_API_KEY environment "
                "variable or pass api_key explicitly."
            )
        # Use the correct model from your list
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        # Alternative: you can also use:
        # self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"
        
        self.request_queue = queue.Queue()
        self.results = {}
        self.running = True
        self.cache = {}
        self.rate_limit = 2
        self.last_request = 0
        self.request_count = 0
        self.daily_limit = 60
        
        # Start worker thread
        self.worker = threading.Thread(target=self.process_queue, daemon=True)
        self.worker.start()
        
        print("🤖 Gemini AI Analyzer initialized")
    
    def process_queue(self):
        """Process analysis requests in background"""
        while self.running:
            try:
                # Get next request from queue
                email_id, email_text, callback = self.request_queue.get(timeout=1)
                
                # Check cache first
                cache_key = hash(email_text[:200])
                if cache_key in self.cache:
                    result = self.cache[cache_key]
                    if callback:
                        callback(email_id, result)
                    self.request_queue.task_done()
                    continue
                
                # Rate limiting
                elapsed = time.time() - self.last_request
                if elapsed < self.rate_limit:
                    time.sleep(self.rate_limit - elapsed)
                
                # Check daily limit
                self.request_count += 1
                if self.request_count > self.daily_limit:
                    print(f"⚠️ Daily API limit reached ({self.daily_limit})")
                    result = self.get_fallback_result(email_text)
                else:
                    # Call Gemini API
                    result = self.analyze_with_gemini(email_text)
                
                self.last_request = time.time()
                
                # Cache result
                self.cache[cache_key] = result
                
                # Store result
                self.results[email_id] = result
                
                # Callback if provided
                if callback:
                    callback(email_id, result)
                
                self.request_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ Gemini analysis error: {e}")
                time.sleep(5)
    
    def analyze_with_gemini(self, email_text):
        """Send email to Gemini for phishing analysis"""
        prompt = self.create_phishing_prompt(email_text)
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "topK": 1,
                "topP": 1,
                "maxOutputTokens": 2048
            }
        }
        
        headers = {
            'Content-Type': 'application/json',
            'x-goog-api-key': self.api_key
        }
        
        try:
            print(f"📡 Sending request to Gemini API...")
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            print(f"📡 Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                return self.parse_gemini_response(result)
            elif response.status_code == 404:
                print("⚠️ Model not found. Using fallback analysis.")
                return self.get_fallback_result(email_text)
            elif response.status_code == 429:
                print("⚠️ Rate limit exceeded. Using fallback analysis.")
                return self.get_fallback_result(email_text)
            else:
                print(f"⚠️ API Error {response.status_code}")
                return self.get_fallback_result(email_text)
                
        except Exception as e:
            print(f"⚠️ API error: {e}")
            return self.get_fallback_result(email_text)
    
    def get_fallback_result(self, email_text):
        """Provide fallback analysis when API fails"""
        reasons = []
        is_phishing = False
        confidence = 0
        
        # Check for common phishing indicators
        if 'http://' in email_text or 'https://' in email_text:
            confidence += 30
            reasons.append("Contains URLs")
        
        urgent_words = ['urgent', 'immediately', 'verify', 'suspended', 'limited']
        for word in urgent_words:
            if word in email_text.lower():
                confidence += 10
                reasons.append(f"Contains '{word}'")
        
        suspicious_domains = ['paypal-security', 'apple-id-verify', 'amazon-security',
                             'bankofamerica-verify', 'irs-gov', 'secure-verify']
        for domain in suspicious_domains:
            if domain in email_text.lower():
                confidence += 20
                reasons.append(f"Suspicious domain pattern")
                is_phishing = True
        
        if confidence > 50:
            is_phishing = True
        
        return {
            'is_phishing': is_phishing,
            'confidence': min(confidence, 100),
            'reasons': reasons[:3],
            'source': 'fallback_rules'
        }
    
    def create_phishing_prompt(self, email_text):
        """Create prompt for Gemini to analyze email"""
        return f"""Analyze this email for phishing attempts. Be specific and detailed.

Email content:
{email_text}

Return a JSON object with these exact fields:
- is_phishing: boolean (true if phishing, false if legitimate)
- confidence: number between 0-100
- reasons: array of strings explaining why
- sender_analysis: string analyzing the sender email
- urgency_level: "low", "medium", or "high"
- suspicious_links: array of suspicious URLs found (empty if none)

Respond with ONLY the JSON, no other text."""
    
    def parse_gemini_response(self, response):
        """Parse Gemini API response"""
        try:
            if 'candidates' in response and len(response['candidates']) > 0:
                candidate = response['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    text = candidate['content']['parts'][0]['text']
                    
                    # Clean up JSON
                    text = text.strip()
                    if text.startswith('```json'):
                        text = text[7:]
                    if text.startswith('```'):
                        text = text[3:]
                    if text.endswith('```'):
                        text = text[:-3]
                    
                    text = text.strip()
                    
                    # Parse JSON
                    result = json.loads(text)
                    
                    # Ensure required fields
                    required_fields = ['is_phishing', 'confidence', 'reasons']
                    for field in required_fields:
                        if field not in result:
                            result[field] = False if field == 'is_phishing' else 0 if field == 'confidence' else []
                    
                    return result
                else:
                    return self.get_default_result()
            else:
                return self.get_default_result()
                
        except Exception as e:
            print(f"⚠️ Parse error: {e}")
            return self.get_default_result()
    
    def get_default_result(self):
        """Return default result when parsing fails"""
        return {
            'is_phishing': False,
            'confidence': 0,
            'reasons': ['Analysis failed'],
            'sender_analysis': 'Unable to analyze',
            'urgency_level': 'unknown',
            'suspicious_links': []
        }
    
    def analyze_email_async(self, email_id, email_text, callback=None):
        """Queue email for async analysis"""
        self.request_queue.put((email_id, email_text, callback))
        return True
    
    def stop(self):
        """Stop the analyzer"""
        self.running = False
        print("🤖 Gemini Analyzer stopped")

# Create singleton instance. Gemini analysis is an optional enhancement, so a
# missing API key shouldn't crash every module that imports this file --
# callers should check `if gemini_analyzer is not None` before using it.
try:
    gemini_analyzer = GeminiAnalyzer()
except ValueError as e:
    print(f"⚠️ {e}")
    gemini_analyzer = None