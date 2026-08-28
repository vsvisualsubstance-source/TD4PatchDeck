{
  "mood": "curiosity",
  "lifeIndex": 50,
  "gamification": {
    "level": 8,
    "xp": 15164,
    "xpNextLevel": 16550,
    "activeClass": "Guerriero",
    "unlockedAssets": [
      "base_grid",
      "ambient_particles_low",
      "shield_dome",
      "rune_circle",
      "glyph_trail",
      "crystal_garden",
      "starfield",
      "phoenix_core"
    ],
    "stats": {
      "mago": 1387,
      "bardo": 127,
      "guerriero": 2371,
      "druido": 1586
    },
    "_cd": {
      "natura": 1787755032180,
      "movimento": 1787925798149,
      "voce": 1787925837010,
      "pensiero": 1787926010920,
      "presenza": 1787744119921,
      "riflessione": 1786827611348,
      "rituale": 1787924020502
    },
    "_lastMemCount": 3,
    "_lastVoiceTs": 1787925835451,
    "_lastThoughtTs": 1787926010547
  },
  "presence": {
    "mauro": {
      "present": true,
      "enterTs": 1787926137598,
      "lastSeen": 1787926184694,
      "room": "soggiorno",
      "confidence": 0.5843,
      "track_id": 2,
      "pose": "standing",
      "exitTs": 1786539599216
    },
    "eli": {
      "present": false,
      "enterTs": 1787918985177,
      "lastSeen": 1787918985177,
      "room": null,
      "confidence": 0.4219,
      "track_id": 24,
      "pose": "standing"
    },
    "nitai": {
      "present": false,
      "enterTs": 1787753419668,
      "lastSeen": 1787753426359,
      "room": null,
      "confidence": 0.49
    },
    "maurizio": {
      "present": false,
      "enterTs": 1787755653213,
      "lastSeen": 1787755653213,
      "room": null,
      "confidence": 0.4606
    }
  },
  "rooms": {
    "corridoio": {
      "people": [],
      "objects": {},
      "ambient_light": 0.9997697679981565,
      "darkness": true,
      "_temps": {
        "hue_temperature_sensor_3_temperatura": 27.07,
        "hue_temperature_sensor_5_temperatura": 26.28
      },
      "temperature": 26.7,
      "lastMotion": 1787925081940
    },
    "salotto": {
      "id": "salotto",
      "name": "salotto",
      "persons_count": 0,
      "objects": {},
      "lastUpdate": 1787926183160,
      "people": [],
      "main_user": "mauro",
      "zone": null,
      "_yolo": true,
      "lastYolo": 1787926183160,
      "activity": "empty",
      "_activityCandidate": "empty",
      "_activityCandidateSince": 1787925924070,
      "_activityCommitted": "present"
    },
    "ingresso": {
      "people": [],
      "objects": {},
      "_temps": {
        "hue_temperature_sensor_4_temperatura": 25.71
      },
      "temperature": 25.7,
      "ambient_light": 0.9997697679981565,
      "darkness": true,
      "lastMotion": 1787925798149,
      "zone": "citofono",
      "persons_count": 0,
      "main_user": null,
      "lastUpdate": 1787925816669,
      "_yolo": true,
      "lastYolo": 1787925813895,
      "activity": "empty",
      "_activityCandidate": "empty",
      "_activityCandidateSince": 1787925813895
    },
    "soggiorno": {
      "id": "soggiorno",
      "name": "soggiorno",
      "persons_count": 1,
      "objects": {},
      "lastUpdate": 1787926184694,
      "people": [
        "mauro"
      ],
      "main_user": "mauro",
      "zone": "unknown",
      "_yolo": true,
      "lastYolo": 1787926140100,
      "activity": "present",
      "_activityCandidate": "present",
      "_activityCandidateSince": 1787926140100,
      "_mediapipe": true,
      "mediapipe": {
        "emotion": "neutral",
        "pose": "standing",
        "attention": "left",
        "smile_score": 22,
        "mouth_open": false,
        "eyes_open": true,
        "gesture": null,
        "people_count": 1,
        "people": [
          {
            "id": 0,
            "emotion": "neutral",
            "smile_score": 22,
            "attention": "left",
            "mouth_open": false,
            "eyes_open": true,
            "pose": "standing",
            "gestures": []
          }
        ],
        "ts": 1787926184694
      },
      "currentPose": "standing",
      "currentEmotion": "neutral",
      "_activityCommitted": "sitting"
    },
    "test": {
      "id": "test",
      "name": "test",
      "persons_count": 0,
      "objects": {},
      "lastUpdate": 1787925287707,
      "people": [],
      "main_user": null,
      "zone": "citofono",
      "_yolo": true,
      "lastYolo": 1787925287707,
      "activity": "empty",
      "_activityCandidate": "empty",
      "_activityCandidateSince": 1787925287707
    }
  },
  "ts": 1787926185406
}