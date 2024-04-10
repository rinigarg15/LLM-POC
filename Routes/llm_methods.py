from llama_index.llms import OpenAI
from ORM.auto_grader_orms import SessionLocal, UserQuestionAnswer
from llama_index.llms.llm import stream_chat_response_to_tokens
from llama_index.llms import ChatMessage
from fastapi.responses import StreamingResponse
from llama_index import ServiceContext
from llama_index.response_synthesizers.tree_summarize import TreeSummarize

def generate_answer_feedback(correct_answer_text, student_answer_text, question, user_question_paper, db):
    grade =  {question.question_paper.grade}
    understanding_level = user_question_paper.understanding_level
    tone = user_question_paper.tone

    prompt = f"""
    question: {question.question_text}
    correct_answer: {correct_answer_text}
    student_answer: {student_answer_text}
    topic: {question.question_paper.topic}

    --------------------------------------------------------
    You are a tutor with a very {tone} style of communication who has been provided the \
    correct_answer and the student_answer to a MCQ question for class {grade} on the given topic. \
    All the 3 fields - correct_answer, student_answer, and question are in LaTeX.
    The student_answer is wrong.
    Your goal is to generate concise feedback to help the student, with the important points highlighted in bold.

    Perform the following actions:
    1) Generate appropriate bulleted feedback in a very {tone} style of communication, \
    structured in 3 concise points, based on the wrong student_answer and the correct_answer and by taking into account\
    both the topic and that the feedback is meant for class {grade} students with a {understanding_level} level understanding on the topic.

    2) Include a "Avoid this mistake in future" section with a concise point in a very {tone} style of communication, \
    based on the wrong student_answer and the correct_answer and by taking into account\
    both the topic and that the feedback is meant for class {grade} students with a {understanding_level} level understanding on the topic, so that the student doesn't reepat the mistake.

    Always enclose any LaTeX compatible component in '$$' for proper rendering in Streamlit. \
    Ensure that ONLY the LaTeX compatible component is within these markers, not the entire text. \
    Do not address the student by saying "Dear student".
    """


    llm = OpenAI(model="gpt-4-1106-preview", temperature = 0)
    message = ChatMessage(role="user", content=prompt)

    response = llm.stream_chat([message])
    stream_tokens = stream_chat_response_to_tokens(response)
    db.close()
    return StreamingResponse(stream_tokens)

def assessment_llm(user_question_paper, db):
    understanding_level = user_question_paper.understanding_level
    tone = user_question_paper.tone

    prompt = f"""
    feedback: {user_question_paper.feedback}
    topic: {user_question_paper.question_paper.topic}
    
    --------------------------------------------------------
    You are a tutor with a very {tone} style of communication who has been given the lines\
    of feedback a student received in taking a MCQ test on the topic.
    Your job is to create a relevant and concise bulleted summary from the individual feedback\
    that can help the student with a {understanding_level} level understanding on the topic hone his preparation.
    Articulate a generic feedback taking cues from the student's mistakes and \
    avoid mentioning individual question feedback.

    Always enclose any LaTeX compatible component in '$$' for proper rendering in Streamlit. \
    Ensure that ONLY the LaTeX compatible component is within these markers, not the entire text. \
    """

    llm = OpenAI(model="gpt-4-1106-preview", temperature = 0)
    message = ChatMessage(role="user", content=prompt)

    response = llm.stream_chat([message])
    stream_tokens = stream_chat_response_to_tokens(response)
    db.close()
    return StreamingResponse(stream_tokens)

def generate_next_steps(correct_answer_text, question, user_question_paper, db):
    grade = question.question_paper.grade
    understanding_level = user_question_paper.understanding_level
    topic = question.question_paper.topic
    tone = user_question_paper.tone

    prompt = f"""
    question: {question.question_text}
    correct_answer: {correct_answer_text}

    --------------------------------------------------------
    You are a tutor with a very {tone} style of communication who has been provided the \
    correct_answer to a MCQ question for class {grade} on the given {topic}. \
    The fields correct_answer and question are in LaTeX.
    The student has answered the question correctly.
    Your goal is to generate concise next steps to help the student, with the important points highlighted in bold.
    Perform the following actions:
    1) Generate appropriate bulleted next steps for a student of class {grade}, \
    with an aim to deepen their understanding on the {topic},\
    in a very {tone} style of communication, structured in 2 concise points,
    by taking into account the fact that the student has a {understanding_level} level understanding of this {topic}.

    Always enclose any LaTeX compatible component in '$$' for proper rendering in Streamlit. \
    Ensure that ONLY the LaTeX compatible component is within these markers, not the entire text. \
    Do not address the student by saying "Dear student".
    """


    llm = OpenAI(model="gpt-4-1106-preview", temperature = 0)
    message = ChatMessage(role="user", content=prompt)

    response = llm.stream_chat([message])
    stream_tokens = stream_chat_response_to_tokens(response)
    db.close()
    return StreamingResponse(stream_tokens)

def next_steps_llm(user_question_paper, db):
    understanding_level = user_question_paper.understanding_level
    tone = user_question_paper.tone
    topic = {user_question_paper.question_paper.topic}

    prompt = f"""
    next_steps: {user_question_paper.next_steps}
    
    --------------------------------------------------------
    You are a tutor with a very {tone} style of communication who has been given the lines\
    of next_steps a student received in taking a MCQ test on the {topic}, to deepen his understanding on the {topic}.
    Your job is to create a relevant and concise bulleted summary from the individual next_steps\
    that can help the student with a {understanding_level} level understanding on the {topic} hone his preparation.
    Articulate a generic summary and avoid mentioning individual question summary.

    Always enclose any LaTeX compatible component in '$$' for proper rendering in Streamlit. \
    Ensure that ONLY the LaTeX compatible component is within these markers, not the entire text. \
    """

    llm = OpenAI(model="gpt-4-1106-preview", temperature = 0)
    message = ChatMessage(role="user", content=prompt)

    response = llm.stream_chat([message])
    stream_tokens = stream_chat_response_to_tokens(response)
    db.close()
    return StreamingResponse(stream_tokens)

def assessment_tree_summarise(user_question_paper):
    db = SessionLocal()
    user_question_answers= db.query(UserQuestionAnswer).filter(UserQuestionAnswer.user_question_paper_id == user_question_paper.id).all()
    topic = user_question_paper.question_paper.topic
    understanding_level = user_question_paper.understanding_level
    tone = user_question_paper.tone

    llm = OpenAI(model="gpt-4")
    service_context = ServiceContext.from_defaults(llm=llm)
    response_synthesizer = TreeSummarize(streaming = True, service_context=service_context)

    query_text = f"""
    You are a tutor with a very {tone} style of communication who has been given the lines\
    of feedback a student received in taking a MCQ test on the {topic}.
    Your job is to create a relevant and concise bulleted summary from the individual feedback\
    that can help the student with a {understanding_level} level understanding on the {topic} hone his preparation.
    Articulate a generic feedback taking cues from the student's mistakes and \
    avoid mentioning individual question feedback.

    Always enclose any LaTeX compatible component in '$$' for proper rendering in Streamlit. \
    Ensure that ONLY the LaTeX compatible component is within these markers, not the entire text. \
    """

    texts = []
    for answer in user_question_answers:
        if not answer.feedback:
            continue
        texts.append(answer.feedback)

    response = response_synthesizer.get_response(
        query_text,
        texts
    )
    db.close()
    return StreamingResponse(response)