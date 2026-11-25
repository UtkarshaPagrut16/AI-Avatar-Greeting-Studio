"""
template_generator.py - The NON-AI fallback greeting generator.

This module does NOT use any AI. It fills fixed, hand-written sentences
with the recipient's name, the sender's name and the personal message.
It is used only when the local LLM is unavailable, so that the rest of the
project (voice, avatar, video) can still be demonstrated.

Every result is labelled source="template" and the UI shows a yellow
"Template fallback - not AI-generated" badge.
"""
import random

# {r} = recipient, {s} = sender, {e} = event name (festival / custom occasion)
ENGLISH = {
    "Birthday": {
        "Friendly": [
            "Hey {r}, happy birthday! I hope today is full of laughter, cake and all your favourite people. You make every day brighter, so enjoy every moment of yours. Have an amazing year ahead! Lots of love, {s}.",
            "Happy birthday, {r}! Another year older and still the most fun person I know. Wishing you big smiles, great food and wonderful surprises today. Cheers from {s}!",
        ],
        "Formal": [
            "Dear {r}, warm wishes on your birthday. May the coming year bring you good health, success and happiness in everything you do. With kind regards, {s}.",
        ],
        "Funny": [
            "Happy birthday, {r}! Don't worry about the number of candles, the fire brigade is on standby. Have a fantastic day and eat as much cake as you like. Your partner in crime, {s}.",
        ],
        "Heartfelt": [
            "Dear {r}, happy birthday. Having you in my life is a gift I am grateful for every single day. I hope this year gives back all the kindness you share with everyone. With all my heart, {s}.",
        ],
    },
    "Anniversary": {
        "Friendly": ["Happy anniversary, {r}! Here is to many more years of love, laughter and adventures together. Have a beautiful celebration! Warm wishes, {s}."],
        "Formal": ["Dear {r}, heartiest congratulations on your anniversary. Wishing you continued happiness and togetherness in the years ahead. Best regards, {s}."],
        "Funny": ["Happy anniversary, {r}! Another year of sharing the remote and still smiling, that is true love. Have a wonderful day! Cheers, {s}."],
        "Heartfelt": ["Dear {r}, happy anniversary. Your bond is a beautiful reminder of what real love looks like. May your journey together stay this special forever. With love, {s}."],
    },
    "Congratulations": {
        "Friendly": ["Congratulations, {r}! You worked so hard for this and you totally deserve it. I am super proud of you. Time to celebrate! Cheers, {s}."],
        "Formal": ["Dear {r}, my sincere congratulations on your achievement. Your dedication and effort are truly commendable. Wishing you continued success. Regards, {s}."],
        "Funny": ["Congratulations, {r}! You did it, and now you are officially too cool to talk to me. Just kidding, I am so proud of you. Party soon! From {s}."],
        "Heartfelt": ["Dear {r}, congratulations. Watching your hard work turn into success fills me with so much pride. You deserve every bit of this happiness. With love, {s}."],
    },
    "Thank You": {
        "Friendly": ["Hey {r}, a huge thank you! Your help meant a lot and made everything so much easier. You are the best. Thanks again, {s}."],
        "Formal": ["Dear {r}, thank you sincerely for your kind support. Your help is truly appreciated. With gratitude, {s}."],
        "Funny": ["Thank you, {r}! You saved the day once again. I owe you one, or maybe ten, but who is counting? Gratefully yours, {s}."],
        "Heartfelt": ["Dear {r}, thank you from the bottom of my heart. Your kindness made a real difference, and I will always remember it. With gratitude, {s}."],
    },
    "Welcome": {
        "Friendly": ["Welcome, {r}! We are so happy to have you here. Make yourself at home and let us know if you need anything. See you soon! From {s}."],
        "Formal": ["Dear {r}, a very warm welcome. We are delighted to have you with us and look forward to working together. Best regards, {s}."],
        "Funny": ["Welcome aboard, {r}! The snacks are in the kitchen and the good chairs go fast, so hurry. Glad you are here! From {s}."],
        "Heartfelt": ["Dear {r}, welcome. We are truly happy you are here, and we hope you feel at home from the very first day. Warmly, {s}."],
    },
    "Festival": {
        "Friendly": ["Happy {e}, {r}! Wishing you and your family a festival full of light, sweets and happy moments together. Enjoy the celebrations! From {s}."],
        "Formal": ["Dear {r}, warm wishes on the occasion of {e}. May this festival bring peace, prosperity and joy to you and your family. Regards, {s}."],
        "Funny": ["Happy {e}, {r}! May your sweets be many and your calories be invisible. Have a fantastic celebration! From {s}."],
        "Heartfelt": ["Dear {r}, happy {e}. May this festival fill your home with warmth, love and togetherness. Thinking of you, {s}."],
    },
    "Custom": {
        "Friendly": ["Hey {r}! Sending you the warmest wishes for {e}. I hope it is a wonderful moment for you. Take care, {s}."],
        "Formal": ["Dear {r}, my best wishes to you on {e}. I hope this occasion brings you happiness and success. Regards, {s}."],
        "Funny": ["Hey {r}! Big wishes for {e}. I tried to write a poem, but this message is all you get. Enjoy! From {s}."],
        "Heartfelt": ["Dear {r}, my heartfelt wishes for {e}. You mean a lot to me, and I hope this moment is truly special. With love, {s}."],
    },
}

# Hinglish (Hindi written in English letters). One template per occasion;
# tone is not varied here because the fallback is only a backup.
HINGLISH = {
    "Birthday": "Happy birthday, {r}! Aapko janamdin ki dher saari shubhkamnayein. Bhagwan aapko hamesha khush aur swasth rakhe. Bahut saara pyaar, {s}.",
    "Anniversary": "Happy anniversary, {r}! Aap dono ka saath hamesha aise hi bana rahe. Dher saari shubhkamnayein, {s}.",
    "Congratulations": "Bahut bahut badhai ho, {r}! Aapki mehnat rang laayi hai. Aise hi aage badhte raho. {s} ki taraf se.",
    "Thank You": "{r}, dil se shukriya! Aapki madad ke liye main bahut aabhaari hoon. Dhanyavaad, {s}.",
    "Welcome": "{r}, aapka swagat hai! Humein bahut khushi hai ki aap humare saath hain. {s} ki taraf se.",
    "Festival": "{r}, aapko {e} ki hardik shubhkamnayein! Yeh tyohaar aapke ghar khushiyan laaye. {s} ki taraf se.",
    "Custom": "{r}, {e} ke liye aapko dher saari shubhkamnayein! {s} ki taraf se.",
}

# Hindi in Devanagari script.
HINDI = {
    "Birthday": "{r}, जन्मदिन की हार्दिक शुभकामनाएँ! आप हमेशा खुश और स्वस्थ रहें। ढेर सारा प्यार, {s}।",
    "Anniversary": "{r}, सालगिरह की हार्दिक बधाई! आपका साथ हमेशा ऐसे ही बना रहे। शुभकामनाओं सहित, {s}।",
    "Congratulations": "{r}, बहुत-बहुत बधाई! आपकी मेहनत रंग लाई है। ऐसे ही आगे बढ़ते रहिए। {s} की ओर से।",
    "Thank You": "{r}, दिल से धन्यवाद! आपकी मदद के लिए मैं बहुत आभारी हूँ। {s}।",
    "Welcome": "{r}, आपका हार्दिक स्वागत है! हमें बहुत खुशी है कि आप हमारे साथ हैं। {s} की ओर से।",
    "Festival": "{r}, आपको {e} की हार्दिक शुभकामनाएँ! यह त्योहार आपके घर खुशियाँ लाए। {s} की ओर से।",
    "Custom": "{r}, {e} के लिए आपको ढेर सारी शुभकामनाएँ! {s} की ओर से।",
}

MESSAGE_LEAD = {"en": "{s} also wants to say: ", "hinglish": "{s} kehna chahte hain: ", "hi": "{s} कहना चाहते हैं: "}


def default_event_name(occasion, occasion_name):
    """Name used for {e}. Festival without a name becomes a generic phrase."""
    if occasion_name:
        return occasion_name
    if occasion == "Festival":
        return "the festival season"
    return occasion.lower()


def generate_template_greeting(details, rng=None):
    """Build a greeting from fixed templates. `details` is the validated form dict."""
    rng = rng or random.Random()
    language = details["language"]
    occasion = details["occasion"]
    values = {
        "r": details["recipient"],
        "s": details["sender"],
        "e": default_event_name(occasion, details.get("occasion_name", "")),
    }

    if language == "hinglish":
        text = HINGLISH[occasion]
    elif language == "hi":
        text = HINDI[occasion]
    else:
        text = rng.choice(ENGLISH[occasion][details["tone"]])
    text = text.format(**values)

    message = details.get("message", "").strip()
    if message:
        if message[-1] not in ".!?।":
            message += "."
        # Add the personal message, word for word, at the end.
        text = f"{text} {MESSAGE_LEAD[language].format(**values)}{message}"
    return text
