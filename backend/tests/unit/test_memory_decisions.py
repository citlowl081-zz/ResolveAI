"""Unit tests for agent memory decision rules."""


from app.agent.memory_decisions import should_not_save, should_save_memory


class TestShouldSaveMemory:
    def test_explicit_remember_jizhu(self) -> None:
        do_save, mem_type, content = should_save_memory(
            user_message="记住我偏好微信沟通",
            response_text="好的，已记录",
            intent="OTHER",
            tool_results=None,
            turn_count=1,
        )
        assert do_save is True
        assert mem_type == "FACT"
        assert "偏好微信沟通" in (content or "")

    def test_explicit_remember_bangwoji(self) -> None:
        do_save, mem_type, content = should_save_memory(
            user_message="帮我记住：下次退款到支付宝",
            response_text="已记录",
            intent="OTHER",
            tool_results=None,
            turn_count=1,
        )
        assert do_save is True
        assert mem_type == "FACT"
        assert "退款到支付宝" in (content or "")

    def test_explicit_remember_baocun(self) -> None:
        do_save, mem_type, content = should_save_memory(
            user_message="保存：我的地址是广州市天河区",
            response_text="好的",
            intent="OTHER",
            tool_results=None,
            turn_count=1,
        )
        assert do_save is True
        assert mem_type == "FACT"

    def test_explicit_remember_without_content(self) -> None:
        do_save, mem_type, content = should_save_memory(
            user_message="帮我记一下",
            response_text="好的，请告诉我您想记什么",
            intent="OTHER",
            tool_results=None,
            turn_count=1,
        )
        assert do_save is True
        assert mem_type == "FACT"

    def test_preference_multi_keyword_turn2(self) -> None:
        do_save, mem_type, content = should_save_memory(
            user_message="下次退款到支付宝，以后都这样",
            response_text="好的",
            intent="QUALITY_REFUND",
            tool_results=None,
            turn_count=2,
        )
        assert do_save is True
        assert mem_type == "PREFERENCE"

    def test_preference_single_keyword_turn3(self) -> None:
        do_save, mem_type, content = should_save_memory(
            user_message="退款方式就用支付宝吧",
            response_text="已记录",
            intent="QUALITY_REFUND",
            tool_results=None,
            turn_count=3,
        )
        assert do_save is True
        assert mem_type == "PREFERENCE"

    def test_preference_single_keyword_turn1_no_save(self) -> None:
        do_save, mem_type, content = should_save_memory(
            user_message="退款到支付宝",
            response_text="好的",
            intent="QUALITY_REFUND",
            tool_results=None,
            turn_count=1,
        )
        # Single keyword, turn 1 — not enough confidence yet
        assert do_save is False

    def test_ticket_resolution_summary(self) -> None:
        do_save, mem_type, content = should_save_memory(
            user_message="谢谢处理",
            response_text="已为您创建工单 TKT-001，状态：已通过审核",
            intent="OTHER",
            tool_results=[{
                "tool_name": "create_after_sales_ticket",
                "is_success": True,
                "data": {"ticket_number": "TKT-001", "status": "APPROVED"},
            }],
            turn_count=2,
        )
        assert do_save is True
        assert mem_type == "SUMMARY"

    def test_no_save_trivial_message(self) -> None:
        do_save, mem_type, content = should_save_memory(
            user_message="你好",
            response_text="您好，请问有什么可以帮您？",
            intent="OTHER",
            tool_results=None,
            turn_count=1,
        )
        assert do_save is False

    def test_no_save_no_triggers(self) -> None:
        do_save, mem_type, content = should_save_memory(
            user_message="我的订单到哪里了",
            response_text="您的订单正在运输中",
            intent="LOGISTICS_INQUIRY",
            tool_results=[],
            turn_count=1,
        )
        assert do_save is False


class TestShouldNotSave:
    def test_logistics_inquiry_not_saved(self) -> None:
        assert should_not_save("查物流") is True
        assert should_not_save("我的快递到哪里了") is True
        assert should_not_save("查看订单状态") is True

    def test_greeting_not_saved(self) -> None:
        assert should_not_save("你好") is True
        assert should_not_save("您好") is True
        assert should_not_save("hi") is True

    def test_thanks_not_saved(self) -> None:
        assert should_not_save("谢谢") is True
        assert should_not_save("好的") is True
        assert should_not_save("OK") is True

    def test_question_not_saved(self) -> None:
        assert should_not_save("能退款吗") is True

    def test_substantive_message_not_filtered(self) -> None:
        assert should_not_save("我要退款，产品质量有问题") is False
        assert should_not_save("记住我下次要支付宝退款") is False
