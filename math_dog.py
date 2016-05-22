'''
Math Dog by BrownDogTech.com

This is code for an Amazon Alexa Skill that is a math quiz game.
This code is designed to run through AWS Lambda service,
and requires no additional Python modules than what is available by default.

Originally Created: May 15, 2016
Modified: May 21, 2016

Author: Hank Preston, hank.preston@gmail.com

'''

# Todo - set time to wait for answer
# Todo - setup "AMAZON.StartOverIntent" to begin a new game.

from __future__ import print_function
from random import randint

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

    Left commented out for sharing on GitHub, set to actual app id when coping to Lambda
    """
    # if (event['session']['application']['applicationId'] !=
    #         "amzn1.echo-sdk-ams.app.c30c2867-91a5-4cc7-8bd3-5148ff1bd18f"):
    #     raise ValueError("Invalid Application ID")

    # Create two main objects from the 'event'
    session = event['session']
    request = event['request']

    # Get or Setup Session Attributes
    # Session Attributes are used to track elements like current question details, last intent/function position, etc
    session_attributes = load_session_attributes(session)
    session["attributes"] = session_attributes

    # Write Session attributes to Lambda log for troubleshooting assistance
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
    """
    Called when the user specifies an intent for this skill.
    Main logic point to determine what action to take based on users
    request.
    """

    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    # Get key details from intent_request object to work with easier
    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    # Find the Previous Place if stored
    # "previous_place" is used to deal with intents and responses that are contextual
    try:
        previous_place = session["attributes"]["previous_place"]
    except:
        previous_place = None

    # Dispatch to your skill's intent handlers
    if intent_name == "AMAZON.HelpIntent":
        # User has asked for help, return the help menu
        return get_help(intent, session)
    elif intent_name == "AMAZON.StopIntent":
        # Built-in intent for when user says something like "Stop"
        if "last_question" in session["attributes"].keys() and previous_place != "verify end game":
            # Have found that Alexa will think the user asked to stop even when that wasn't desired
            # This if statement checks to see if user was in the middle of a game,
            # and wasn't already asked if they "really wanted to stop"
            # If so, reply back to verify that ending was really desired.
            return verify_end_game(intent, session)
        # Standard End Game Message
        return no_more(intent, session)
    elif intent_name == "AMAZON.CancelIntent":
        # Built-in intent for when user says something like "Cancel"
        if "last_question" in session["attributes"].keys() and previous_place != "verify end game":
            # Have found that Alexa will think the user asked to stop even when that wasn't desired
            # This if statement checks to see if user was in the middle of a game,
            # and wasn't already asked if they "really wanted to stop"
            # If so, reply back to verify that ending was really desired.
            return verify_end_game(intent, session)
        # Standard End Game Message
        return no_more(intent, session)
    elif intent_name == "DifficultyMenu":
        # When user asks to change the difficulty
        # Provide some details on difficulty levels and ask if they want to change the level
        return difficulty_menu(intent, session)
    elif intent_name == "SetDifficulty":
        # When explicit request to change the difficulty was made
        return set_difficulty(intent, session)
    elif intent_name == "SetRoundLength":
        # When explicit request to change the round length was made
        return set_roundlength(intent, session)
    elif intent_name == "StartGame":
        # Verify not in the middle of a game, if so, repeat last question
        if "last_question" in session["attributes"].keys():
            repeat_question(intent, session)
        return play_game(intent, session)
    elif intent_name == "NumericResponse":
        # When user states a number like "7" or "23"
        # Depending on what the user was last asked, this type of response needs
        # different actions.
        # Find the Previous Place to deduce where to go next
        if previous_place == "difficulty menu":
            # This would be in response to question "What difficulty level would you like to set?"
            return set_difficulty(intent,session)
        elif previous_place in ["ask problem", "play game"]:
            # This would be as an answer to a math problem
            # Verify answer is audible, if not repeat the question
            try:
                answer_given = int(intent["slots"]["Number"]["value"])
            except ValueError:
                return repeat_question(intent, session)
            return play_game(intent,session)
        else:
            # if a number is given when the previous place or question wouldn't indicate
            # a number to be expected, end the game
            return no_more(intent, session)
    elif intent_name == "AMAZON.YesIntent":
        # For when user provides an answer like "Yes"
        # Depending on the previous question asked, differnet actions must be taken
        if previous_place in ["set difficulty", "get help", "welcome", "play game", "set round length"]:
            # Typically means that the user was just asked "Do you want to play a game?"
            # Verify not in the middle of a game, if so, repeat last question
            if "last_question" in session["attributes"].keys():
                return repeat_question(intent, session)
            return play_game(intent, session)
        elif previous_place in ["verify end game"]:
            # When verifying that a user wants to end a game, Alexa asks:
            # "Do you want to end?"
            return no_more(intent, session)
        else:
            # If the a "Yes" response wouldn't make sense based on previous place, end game
            return no_more(intent, session)
    elif intent_name == "AMAZON.NoIntent":
        # For when user provides an answer like "No"
        # Depending on the previous question asked, differnet actions must be taken
        if previous_place in ["verify end game"]:
            # When verifying that a user wants to end a game, Alexa asks:
            # "Do you want to end?"
            # If they say "No" then repeat the last question
            return repeat_question(intent, session)
        elif "last_question" in session["attributes"].keys() and previous_place != "verify end game":
            # If in the middle of a game, and user says "No"
            # see if they really want to end, or if we misunderstood them
            return verify_end_game(intent, session)
        else:
            # Default action to end game
            return no_more(intent, session)
    else:
        # If an intent doesn't match anythign above, it is unexpected
        # and raise error.  This is mostly here for development and troubleshooting.
        # Should NOT occur during normal use.
        raise ValueError("Invalid intent")

def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.

    Is not called when the skill returns should_end_session=true
    """
    print("on_session_ended requestId=" + session_ended_request['requestId'] + ", sessionId=" + session['sessionId'])
    # add cleanup logic here

# --------------- Functions that control the skill's Intents ------------------
def get_welcome_response(request, session):
    """
    Welcome the user to the application and provide instructions to get started.
    """

    # Setup the response details
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
    """
    Main function for Math Dog game
    """

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

        # Adjust difficulty.  If user got better than 80% correct, get harder.
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
    Help function for the skill.
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

def difficulty_menu(intent, session):
    '''
    Generate a menu on the difficulty setting, and ask user to change level.
    '''
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
    '''
    Change difficulty level.
    '''
    # Make sure we have a valid level to use.
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
    '''
    Change the number of questions asked in each round.
    '''
    # Verify that we have a valid number to use.
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

def verify_end_game(intent, session):
    '''
    Function used when user seemed to have asked to end, but currently in the middle of a game.
    '''
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
    '''
    User has indicated they are done.  Provide a message closing the game, and end session.
    '''
    reprompt_text = None
    card_title = "Goodbye for now!"

    text = "Great job today.  Your skills are looking great.  Come back soon.  "
    speech_output = "<speak>" \
                    + text + \
                    "</speak>"
    should_end_session = True

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
    '''
    Get a new question based on the current difficulty level.
    '''

    # Get current difficulty
    d = levels[difficulty]
    # Randomly pick an operation (add, subtract, etc) valid for the level
    operation_index = randint(0,len(d["operations"])-1)
    operation = d["operations"][operation_index]
    # Randomly pick the two math terms based on ranges in the diffuclty level for the operation
    term_1 = randint(operation["term_1_low_range"], operation["term_1_high_range"])
    term_2 = randint(operation["term_2_low_range"], operation["term_2_high_range"])

    # make sure term_1 is larger than term_2, otherwise switch the order
    # Used to keep the answers from going negative
    if term_1 < term_2:
        temp = term_1
        term_1 = term_2
        term_2 = temp

    # Create question details based on the operation
    # Details are: answer, and text
    if operation["operation"] == "add":
        answer = term_1 + term_2
        question_text = "What is %s plus %s" % (term_1, term_2)
        print("Question is: %s + %s = %s." % (term_1, term_2, answer))
    if operation["operation"] == "subtract":
        answer = term_1 - term_2
        question_text = "What is %s minus %s" % (term_1, term_2)
        print("Question is: %s - %s = %s." % (term_1, term_2, answer))
    if operation["operation"] == "multiply":
        answer = term_1 * term_2
        question_text = "What is %s times %s" % (term_1, term_2)
        print("Question is: %s * %s = %s." % (term_1, term_2, answer))
    if operation["operation"] == "divide":
        # Division has a few other checks to keep answers as integers
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

    # Create the question object to return
    question = {
        "question_text": question_text,
        "operation": operation["operation"],
        "term_1": term_1,
        "term_2": term_2,
        "answer": answer
    }
    return question

def get_encouragement(correct):
    '''
    Provide a nice message back to user based on whether their last answer was right or wrong.
    '''
    if correct:
        message = encouragements["correct"][randint(0, len(encouragements["correct"])-1)]
        return message
    else:
        message = encouragements["incorrect"][randint(0, len(encouragements["incorrect"])-1)]
        return message

def load_session_attributes(session):
    '''
    Determine either current, or new session_attributes
    '''
    try:
        # First try to pull from existing session
        session_attributes = session["attributes"]
    except:
        # If fails, this is a new session and create new attributes
        session_attributes = setup_session_attributes()
    return session_attributes

def setup_session_attributes():
    '''
    Sets up initial Math Dog Session Attributes if new session.
    '''
    session_attributes = {}
    session_attributes["difficulty"] = default_difficulty
    session_attributes["question_count"] = 0
    session_attributes["number_correct"] = 0
    session_attributes["number_incorrect"] = 0
    session_attributes["round_length"] = default_round_length
    return session_attributes

# ---------------- Default Settings and Skill Settings -------------------------
# Todo - add support for difficulty of "easy", "medium", etc
# Todo - add support for grades, maybe new levels for common core

# Dictionary object that defines the details of each level
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

# Default settings
default_difficulty = 1
default_round_length = 4

# Dictionary Ojbect that hold the different encouraging messages back to users.
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
