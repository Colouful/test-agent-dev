from backend.schemas.question import QuestionCreate, QuestionListOut, QuestionOut, QuestionUpdate


def test_question_create_minimal():
    q = QuestionCreate(content="题目", correct_answer="答案")
    assert q.wrong_answer is None
    assert q.subject is None


def test_question_create_full():
    q = QuestionCreate(
        content="题目",
        correct_answer="答案",
        wrong_answer="错误答案",
        subject="数学",
        question_type="single",
        image_key="user1/original/abc.jpg",
        confidence=0.9,
        original_filename="photo.jpg",
    )
    assert q.confidence == 0.9


def test_question_update_all_optional():
    # 空更新不报错
    u = QuestionUpdate()
    assert u.content is None


def test_question_out_has_image_url_fields():
    fields = QuestionOut.model_fields
    assert "image_url" in fields
    assert "image_url_expires_at" in fields
    # S3 原始 key 不在响应中暴露
    assert "image_key" not in fields


def test_question_list_out_structure():
    fields = QuestionListOut.model_fields
    assert "items" in fields
    assert "total" in fields
    assert "limit" in fields
    assert "offset" in fields
