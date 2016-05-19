'''
Math Dog by BrownDogTech.com
This is code for an Amazon Alexa Skill that is a math quiz game.
This code is designed to run through AWS Lambda service,
and requires no additional Python modules than what is available by default.

Originally Created: May 15, 2016
Modified: May 15, 2016

Author: Hank Preston, hank.preston@gmail.com

'''

from __future__ import print_function
from pprint import pprint
from random import randint
import json

# --------------- Helpers that build all of the responses ----------------------

def build_speechlet_response(title, output, reprompt_text, card_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'SSML',
            'ssml': output
        },
        'card': {
            'type': 'Simple',
            'title': title,
            'content': card_text
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'SSML',
                'ssml': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }

def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }

# Todo - add "confirm" before no_more
# Todo - set time to wait for answer
# Todo - setup "AMAZON.StartOverIntent" to begin a new game.

# --------------- Handle Incoming Requests -------------------------------------
def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    print("Full Incoming Event Details: " + str(event))

    print("event.session.application.applicationId=" + event['session']['application']['applicationId'])

    """
    Uncomment this if statement and populate with your skill's application ID to
    prevent someone else from configuring a skill that sends requests to this
    function.
    """
    # if (event['session']['application']['applicationId'] !=
    #         "amzn1.echo-sdk-ams.app.c30c2867-91a5-4cc7-8bd3-5148ff1bd18f"):
    #     raise ValueError("Invalid Application ID")

    # Create two main objects from the 'event'
    session = event['session']
    request = event['request']

    # Get or Setup Session Attributes
    session_attributes = load_session_attributes(session)
    session["attributes"] = session_attributes

    print("Session Attributes: " + str(session["attributes"]))
    # pprint(session["attributes"])

    if session['new']:
        on_session_started({'requestId': request['requestId']}, session)

    if request['type'] == "LaunchRequest":
        return on_launch(request, session)
    elif request['type'] == "IntentRequest":
        return on_intent(request, session)
    elif request['type'] == "SessionEndedRequest":
        return on_session_ended(request, session)

def on_session_started(session_started_request, session):
    """ Called when the session starts """
    print("on_session_started requestId=" + session_started_request['requestId'] + ", sessionId=" + session['sessionId'])

def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """
    print("on_launch requestId=" + launch_request['requestId'] + ", sessionId=" + session['sessionId'])
    # Dispatch to your skill's launch
    return get_welcome_response(launch_request, session)

def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill """

    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    # Find the Previous Place if stored
    try:
        previous_place = session["attributes"]["previous_place"]
    except:
        previous_place = None

    # Dispatch to your skill's intent handlers
    if intent_name == "AMAZON.HelpIntent":
        # might be okay already based on repeat logic in play_game
        return get_help(intent, session)
    elif intent_name == "AMAZON.StopIntent":
        # Todo - add logic to verify user wants to end when getting this message
        if "last_question" in session["attributes"].keys() and previous_place != "verify end game":
            return verify_end_game(intent, session)

        return no_more(intent, session)
    elif intent_name == "AMAZON.CancelIntent":
        # Todo - add logic to verify user wants to end when getting this message
        if "last_question" in session["attributes"].keys() and previous_place != "verify end game":
            return verify_end_game(intent, session)
        return no_more(intent, session)
    elif intent_name == "DifficultyMenu":
        return difficulty_menu(intent, session)
    elif intent_name == "SetDifficulty":
        return set_difficulty(intent, session)
    elif intent_name == "SetRoundLength":
        return set_roundlength(intent, session)
    elif intent_name == "StartGame":
        # Verify not in the middle of a game, if so, repeat last question
        if "last_question" in session["attributes"].keys():
            repeat_question(intent, session)
        return play_game(intent, session)
    elif intent_name == "NumericResponse":
        # Find the Previous Place to deduce where to go next
        if previous_place == "difficulty menu":
            return set_difficulty(intent,session)
        elif previous_place in ["ask problem", "play game"]:
            # Verify answer is audible
            try:
                answer_given = int(intent["slots"]["Number"]["value"])
            except ValueError:
                return repeat_question(intent, session)
            # return check_answer(intent,session)
            return play_game(intent,session)
        else:
            return no_more(intent, session)
    elif intent_name == "AMAZON.YesIntent":
        if previous_place in ["set difficulty", "get help", "welcome", "play game", "set round length"]:
            # Verify not in the middle of a game, if so, repeat last question
            if "last_question" in session["attributes"].keys():
                return repeat_question(intent, session)
            # return ask_problem(intent, session)
            return play_game(intent, session)
        elif previous_place in ["verify end game"]:
            # End Game
            return no_more(intent, session)
        else:
            return no_more(intent, session)
    elif intent_name == "AMAZON.NoIntent":
        if previous_place in ["verify end game"]:
            # End Game
            return repeat_question(intent, session)
        elif "last_question" in session["attributes"].keys() and previous_place != "verify end game":
            return verify_end_game(intent, session)
        else:
            return no_more(intent, session)

    else:
        raise ValueError("Invalid intent")

def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.

    Is not called when the skill returns should_end_session=true
    """
    print("on_session_ended requestId=" + session_ended_request['requestId'] + ", sessionId=" + session['sessionId'])
    # add cleanup logic here

# --------------- Functions that control the skill's Intents ------------------
def get_welcome_response(request, session):
    """ If we wanted to initialize the session to have some attributes we could
    add those here
    """

    card_title = "Welcome to Math Dog."
    text = "Welcome to Math Dog, your personal math tutor.  " \
        "Are you ready to begin a game?  "
    speech_output = "<speak>" + text + "</speak>"

    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = "<speak>Want to play a game?  </speak>"
    should_end_session = False

    session["attributes"]["previous_place"] = "welcome"

    return build_response(
        session["attributes"],
        build_speechlet_response(
            card_title,
            speech_output,
            reprompt_text,
            text,
            should_end_session
        )
    )

def play_game(intent, session):
    """ If we wanted to initialize the session to have some attributes we could
    add those here
    """

    # Ways to enter this function
    # 1 - Brand New Game - "begin game"
    # 2 - Answering a Question - "7"

    # # 1 Things to do in this function
    # 1 - clear stats
    # 2 - Notify New Game

    # # 2 Things to do in this function
    # 1 - Check answer of previous question
    # 2 - Provide encouragement

    # Ways to exit this function
    # 1 - Ask a Question
    # 2 - End Game

    # Information Setup for Question
    card_title = ""
    card_text = ""
    speech_output = ""
    reprompt_text = ""
    encouragement = ""
    last_question = None
    next_question = None
    game_details = session["attributes"]

    # How did we enter - New Game, or Continued
    # Look for "last_question" and/or "question_count"
    if "last_question" in game_details.keys():
        # CONTINUE GAME, CHECK ANSWER
        last_question = game_details["last_question"]
        # This verifies that we have a valid answer to check, if not repeat
        try:
            if 'Number' in intent['slots']:
                answer_given = int(intent["slots"]["Number"]["value"])
            else:
                text = "I couldn't tell your answer... try again."
        except KeyError:
            # Repeat question, didn't get an answer
            return repeat_question(intent, session)
        # Test if answer was correct
        if last_question["answer"] == answer_given:
            correct = True
            session["attributes"]["number_correct"] += 1
            print("Correct Answer Given!!!")
        else:
            correct = False
            session["attributes"]["number_incorrect"] += 1
            print("Wrong Answer Given!!!")
        # Get Encouraging message to include in response
        encouragement = get_encouragement(correct)
    else:
        # NEW GAME, NO ANSWER TO CHECK
        # Potentially Clear Stats... but now clearing when game finishes
        pass

    # If will be asking new question, get question
    if game_details["question_count"] < session["attributes"]["round_length"]:
        next_question = get_question(game_details["difficulty"])
        # Update Question in Session for Next Round
        session["attributes"]["last_question"] = next_question
        session["attributes"]["question_count"] += 1

        # Setup Response Objects
        if not last_question:
            # This is the first question in a round
            card_title = "Let's start a Math Quiz!"
        else:
            card_title = "Question #%s." % (session["attributes"]["question_count"])

        card_text = encouragement + next_question["question_text"]
        speech_output = "<speak>" + encouragement + next_question["question_text"] + "</speak>"
        reprompt_text = "<speak>" + next_question["question_text"] + "</speak>"
    else:
        # Game round is over
        # Calculate Results
        grade = session["attributes"]["number_correct"] / session["attributes"]["question_count"]
        result_text = "You got %s out of %s questions correct.  " % (session["attributes"]["number_correct"],  session["attributes"]["question_count"])

        # Adjust difficulty
        if grade > .80:
            new_difficulty = session["attributes"]["difficulty"] + 1
            session["attributes"]["difficulty"] = new_difficulty
            result_text += "You did so well, I'm raising your difficulty to level %s.  " % (new_difficulty)
        else:
            result_text += "You need a bit more practice, I'm leaving your difficulty at level %s.  " % session["attributes"]["difficulty"]

        # Clear Stats
        session["attributes"]["number_correct"] = 0
        session["attributes"]["number_incorrect"] = 0
        session["attributes"]["question_count"] = 0
        del(session["attributes"]["last_question"])

        # Prep response objects
        card_title = "Math Quiz Round Over"
        card_text = result_text
        speech_output = "<speak>" + result_text + "Would you like to play another round?</speak>"
        reprompt_text = "<speak>Would you like to play another round?</speak>"

    # Build output
    should_end_session = False
    session["attributes"]["previous_place"] = "play game"

    # print("Building Question Response.")
    return build_response(
        session["attributes"],
        build_speechlet_response(
            card_title,
            speech_output,
            reprompt_text,
            card_text,
            should_end_session
        )
    )

def repeat_question(intent, session):
    'Used when the provided answer was not clear'
    print("Repeating Question")

    # Details that will be needed
    card_title = ""
    card_text = ""
    speech_output = ""
    reprompt_text = ""
    encouragement = ""
    last_question = None
    next_question = None
    game_details = session["attributes"]

    # Retrieve last question from Session
    next_question = game_details["last_question"]
    card_title = "Repeat Question #%s." % (session["attributes"]["question_count"])
    card_text = next_question["question_text"]
    speech_output = "<speak>"
    if game_details["previous_place"] != "verify end game":
        # leave off this phrase if coming from verifying end game
        speech_output += "I didn't catch your answer, please try again.  "
    speech_output += next_question["question_text"] + "</speak>"
    reprompt_text = "<speak>" + next_question["question_text"] + "</speak>"

    # Build output
    should_end_session = False
    session["attributes"]["previous_place"] = "play game"

    return build_response(
        session["attributes"],
        build_speechlet_response(
            card_title,
            speech_output,
            reprompt_text,
            card_text,
            should_end_session
        )
    )

def get_help(intent, session):
    '''
    Help function for the skill
    :return:
    '''

    card_title = "Math Dog Help"
    text = "Looking for help?  Math Dog is easy to use.  " \
           "To get started, just say 'Begin Game', or just 'Begin'.  " \
           "After I ask you a question, just say your answer.  " \
           "The current difficulty level is level " + str(session["attributes"]["difficulty"]) + ".  " \
           "To change the difficulty level, say 'Change Difficulty', and listen to the instructions. " \
           "Each round will have " + str(session["attributes"]["round_length"]) + " questions.  " \
           "To change the number of questions per round say 'Ask 5 questions per round', and " \
           "rounds will have 5 questions from now on.  "
    speech_output = "<speak>" \
                    + text + \
                    "<break time=\"500ms\" />" \
                    "Would you like to begin a game?  " \
                    "</speak>"

    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = "<speak>Well, do you want to begin a game?  </speak>"
    should_end_session = False

    session["attributes"]["previous_place"] = "get help"

    return build_response(
        session["attributes"],
        build_speechlet_response(
            card_title,
            speech_output,
            reprompt_text,
            text,
            should_end_session
        )
    )

def verify_end_game(intent, session):
    print("Verifying request to end mid-game")

    card_title = "Are you sure you want to end the game?"
    card_text = "I think you asked to stop the game, but we aren't done... do you really want to stop?"
    speech_output = "<speak>" + card_text + "</speak>"
    reprompt_text = "<speak>Do you really want to stop?</speak>"

    # Build output
    should_end_session = False
    session["attributes"]["previous_place"] = "verify end game"

    return build_response(
        session["attributes"],
        build_speechlet_response(
            card_title,
            speech_output,
            reprompt_text,
            card_text,
            should_end_session
        )
    )

def no_more(intent, session):
    reprompt_text = None
    card_title = "Goodbye for now!"

    text = "Great job today.  Your skills are looking great.  Come back soon.  "
    speech_output = "<speak>" \
                    + text + \
                    "</speak>"
    should_end_session = True

    # the user. If the user does not respond or says something that is not
    # understood, the session will end.
    return build_response(
        session["attributes"],
        build_speechlet_response(
            card_title,
            speech_output,
            reprompt_text,
            text,
            should_end_session
        )
    )

def difficulty_menu(intent, session):
    card_title = "Math Dog Difficulty Settings"
    text = "Math Dog will get more challenging as you answer more questions correctly.  " \
           "Difficulty levels range from 1 to 10, and games are currently at " \
           "level " + str(session["attributes"]["difficulty"]) + ".  " \
           "You can change the current difficulty level to Level 3 by saying 'Set Difficulty to 3', " \
           "or to Level 6 by saying 'Set Difficulty to 6'.  "
    speech_output = "<speak>" \
                    + text + \
                    "<break time=\"500ms\" />" \
                    "What difficulty level would you like to set?  " \
                    "</speak>"

    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = "<speak>What difficulty level would you like to set?  </speak>"
    should_end_session = False

    session["attributes"]["previous_place"] = "difficulty menu"

    return build_response(
        session["attributes"],
        build_speechlet_response(
            card_title,
            speech_output,
            reprompt_text,
            text,
            should_end_session
        )
    )

def set_difficulty(intent, session):
    if 'Number' in intent['slots']:
        difficulty = int(intent["slots"]["Number"]["value"])
        if difficulty < 0: difficulty = 0
        if difficulty > 10: difficulty = 10
        session["attributes"]["difficulty"] = difficulty
        text = "The difficulty is now set to level %s.  " % (difficulty)
    else:
        text = "I couldn't tell what difficulty level you asked for, it remains set at level %s.  " % (session["attributes"]["difficulty"])

    card_title = "Math Dog Difficulty Settings"
    speech_output = "<speak>" \
                    + text + \
                    "<break time=\"500ms\" />" \
                    "Would you like to start a game?  " \
                    "</speak>"

    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = "<speak>Would you like to start a game?  </speak>"
    should_end_session = False

    session["attributes"]["previous_place"] = "set difficulty"

    return build_response(
        session["attributes"],
        build_speechlet_response(
            card_title,
            speech_output,
            reprompt_text,
            text,
            should_end_session
        )
    )

def set_roundlength(intent, session):
    if 'Number' in intent['slots']:
        round_length = int(intent["slots"]["Number"]["value"])
        if round_length < 2: round_length = 2
        if round_length > 20: round_length = 20
        session["attributes"]["round_length"] = round_length
        text = "The round length is now set to %s.  " % (round_length)
    else:
        text = "I couldn't tell what round length you asked for, it remains set at %s.  " % (session["attributes"]["round_length"])

    card_title = "Math Dog Round Length Setting"
    speech_output = "<speak>" \
                    + text + \
                    "<break time=\"500ms\" />" \
                    "Would you like to start a game?  " \
                    "</speak>"

    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = "<speak>Would you like to start a game?  </speak>"
    should_end_session = False

    session["attributes"]["previous_place"] = "set round length"

    return build_response(
        session["attributes"],
        build_speechlet_response(
            card_title,
            speech_output,
            reprompt_text,
            text,
            should_end_session
        )
    )

# ---------------- Functions to generate needed information --------------------
def get_question(difficulty):
    d = levels[difficulty]
    operation_index = randint(0,len(d["operations"])-1)
    operation = d["operations"][operation_index]
    term_1 = randint(operation["term_1_low_range"], operation["term_1_high_range"])
    term_2 = randint(operation["term_2_low_range"], operation["term_2_high_range"])
    # make sure term_1 is larger than term_2, otherwise switch the order
    if term_1 < term_2:
        temp = term_1
        term_1 = term_2
        term_2 = temp
    if operation["operation"] == "add":
        answer = term_1 + term_2
        question_text = "What is %s plus %s" % (term_1, term_2)
        print("Question is: %s + %s = %s." % (term_1, term_2, answer))
    if operation["operation"] == "subtract":
        # make sure term_1 is larger than term_2
        answer = term_1 - term_2
        question_text = "What is %s minus %s" % (term_1, term_2)
        print("Question is: %s - %s = %s." % (term_1, term_2, answer))
    if operation["operation"] == "multiply":
        answer = term_1 * term_2
        question_text = "What is %s times %s" % (term_1, term_2)
        print("Question is: %s * %s = %s." % (term_1, term_2, answer))
    if operation["operation"] == "divide":
        # Don't divide by 0
        while term_2 == 0:
            term_2 = randint(1, operation["term_2_high_range"])
        # Make sure the division problem results in integers
        while term_1%term_2 != 0:
            term_1 = randint(operation["term_1_low_range"], operation["term_1_high_range"])
            term_2 = randint(1, operation["term_2_high_range"])

        answer = term_1 / term_2
        question_text = "What is %s divided by %s" % (term_1, term_2)
        print("Question is: %s / %s = %s." % (term_1, term_2, answer))
    question = {
        "question_text": question_text,
        "operation": operation["operation"],
        "term_1": term_1,
        "term_2": term_2,
        "answer": answer
    }
    return question

def get_encouragement(correct):
    if correct:
        message = encouragements["correct"][randint(0, len(encouragements["correct"])-1)]
        return message
    else:
        message = encouragements["incorrect"][randint(0, len(encouragements["incorrect"])-1)]
        return message

def setup_session_attributes():
    'Sets up initial Math Dog Session'
    session_attributes = {}
    session_attributes["difficulty"] = default_difficulty
    session_attributes["question_count"] = 0
    session_attributes["number_correct"] = 0
    session_attributes["number_incorrect"] = 0
    session_attributes["round_length"] = default_round_length
    return session_attributes

def load_session_attributes(session):
    try:
        session_attributes = session["attributes"]
        # print("Current Session Attributes: ")
        # print(session_attributes)
    except:
        # print("Session Attributes not found, creating default: ")
        session_attributes = setup_session_attributes()
        # print(session_attributes)
    return session_attributes

    # if "Joke Category" in session.get('attributes', {}):
    #     session_attributes["Joke Category"] = session["attributes"]["Joke Category"]

# ---------------- Default Settings and Skill Settings -------------------------
# Todo - add support for difficulty of "easy", "medium", etc
# Todo - add support for grades, maybe new levels for common core
# Skill Details
levels = \
    [
        {
            "level": 0,
            "operations": [
                {
                    "operation": "add",
                    "term_count": 2,
                    "term_1_low_range": 0,
                    "term_1_high_range": 5,
                    "term_2_low_range": 0,
                    "term_2_high_range": 5,
                }
            ]
        },
        {
            "level": 1,
            "operations": [
                {
                    "operation": "add",
                    "term_count": 2,
                    "term_1_low_range": 0,
                    "term_1_high_range": 10,
                    "term_2_low_range": 0,
                    "term_2_high_range": 10,
                }
            ]
        },
        {
            "level": 2,
            "operations": [
                {
                    "operation": "subtract",
                    "term_count": 2,
                    "term_1_low_range": 0,
                    "term_1_high_range": 10,
                    "term_2_low_range": 0,
                    "term_2_high_range": 10,
                }
            ]
        },
        {
            "level": 3,
            "operations": [
                {
                    "operation": "add",
                    "term_count": 2,
                    "term_1_low_range": 0,
                    "term_1_high_range": 10,
                    "term_2_low_range": 0,
                    "term_2_high_range": 10,
                },
                {
                    "operation": "subtract",
                    "term_count": 2,
                    "term_1_low_range": 0,
                    "term_1_high_range": 10,
                    "term_2_low_range": 0,
                    "term_2_high_range": 10,
                }
            ]
        },
        {
            "level": 4,
            "operations": [
                {
                    "operation": "add",
                    "term_count": 2,
                    "term_1_low_range": 0,
                    "term_1_high_range": 20,
                    "term_2_low_range": 0,
                    "term_2_high_range": 10,
                },
                {
                    "operation": "subtract",
                    "term_count": 2,
                    "term_1_low_range": 0,
                    "term_1_high_range": 20,
                    "term_2_low_range": 0,
                    "term_2_high_range": 10,
                }
            ]
        },
        {
            "level": 5,
            "operations": [
                {
                    "operation": "multiply",
                    "term_count": 2,
                    "term_1_low_range": 0,
                    "term_1_high_range": 5,
                    "term_2_low_range": 0,
                    "term_2_high_range": 5,
                }
            ]
        },
        {
            "level": 6,
            "operations": [
                {
                    "operation": "add",
                    "term_count": 2,
                    "term_1_low_range": 0,
                    "term_1_high_range": 20,
                    "term_2_low_range": 0,
                    "term_2_high_range": 10,
                },
                {
                    "operation": "subtract",
                    "term_count": 2,
                    "term_1_low_range": 0,
                    "term_1_high_range": 20,
                    "term_2_low_range": 0,
                    "term_2_high_range": 10,
                },
                {
                    "operation": "multiply",
                    "term_count": 2,
                    "term_1_low_range": 0,
                    "term_1_high_range": 5,
                    "term_2_low_range": 0,
                    "term_2_high_range": 5,
                }
            ]
        },
        {
            "level": 7,
            "operations": [
                {
                    "operation": "multiply",
                    "term_count": 2,
                    "term_1_low_range": 0,
                    "term_1_high_range": 10,
                    "term_2_low_range": 0,
                    "term_2_high_range": 10,
                }
            ]
        },
        {
            "level": 8,
            "operations": [
                {
                    "operation": "add",
                    "term_count": 2,
                    "term_1_low_range": 0,
                    "term_1_high_range": 20,
                    "term_2_low_range": 0,
                    "term_2_high_range": 20,
                },
                {
                    "operation": "subtract",
                    "term_count": 2,
                    "term_1_low_range": 0,
                    "term_1_high_range": 20,
                    "term_2_low_range": 0,
                    "term_2_high_range": 20,
                },
                {
                    "operation": "multiply",
                    "term_count": 2,
                    "term_1_low_range": 0,
                    "term_1_high_range": 10,
                    "term_2_low_range": 0,
                    "term_2_high_range": 10,
                }
            ]
        },
        {
            "level": 9,
            "operations": [
                {
                    "operation": "divide",
                    "term_count": 2,
                    "term_1_low_range": 0,
                    "term_1_high_range": 10,
                    "term_2_low_range": 0,
                    "term_2_high_range": 10,
                }
            ]
        },
        {
            "level": 10,
            "operations": [
                {
                    "operation": "add",
                    "term_count": 2,
                    "term_1_low_range": 0,
                    "term_1_high_range": 20,
                    "term_2_low_range": 0,
                    "term_2_high_range": 20,
                },
                {
                    "operation": "subtract",
                    "term_count": 2,
                    "term_1_low_range": 0,
                    "term_1_high_range": 20,
                    "term_2_low_range": 0,
                    "term_2_high_range": 20,
                },
                {
                    "operation": "multiply",
                    "term_count": 2,
                    "term_1_low_range": 0,
                    "term_1_high_range": 10,
                    "term_2_low_range": 0,
                    "term_2_high_range": 10,
                },
                {
                    "operation": "divide",
                    "term_count": 2,
                    "term_1_low_range": 0,
                    "term_1_high_range": 10,
                    "term_2_low_range": 0,
                    "term_2_high_range": 10,
                }
            ]
        }
    ]

default_difficulty = 1
default_round_length = 4

encouragements = {
    "correct": [
        "Way to go!  ",
        "Awesome job!  ",
        "Great!  ",
        "Keep up the good work!  ",
        "Another one correct!  ",
        "You're on fire!  ",
        "Well done!  "
    ],
    "incorrect": [
        "Better luck next time.  ",
        "Close, but not quite.  ",
        "Nope, but keep going.  ",
        "You'll get the next one.  ",
        "So close.  ",
        "Wrong, but don't give up.  "
    ]
}
