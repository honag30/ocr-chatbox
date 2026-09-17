import re
from typing import List
from .schemas import ConflictItem, ConflictValue, EvidenceFact

class ConflictDetector:
    """
    Detects contradictions within a single document or across referenced documents.
    Outputs ConflictItems with status REVIEW_REQUIRED when conflicting values are found.
    """

    @staticmethod
    def detect_conflicts(facts: List[EvidenceFact], related_facts: List[EvidenceFact] = None) -> List[ConflictItem]:
        conflicts: List[ConflictItem] = []

        # 1. Check for conflicting TOTAL_AMOUNT values
        total_amounts = [f for f in facts if f.fact_type in ["TOTAL_AMOUNT", "GROSS_AMOUNT", "AMOUNT"]]
        if len(total_amounts) >= 2:
            val_set = set(float(a.value) for a in total_amounts if isinstance(a.value, (int, float)))
            if len(val_set) > 1:
                conflicts.append(
                    ConflictItem(
                        field="amount",
                        values=[
                            ConflictValue(value=a.value, source=f"Fact {a.evidence_fact_id} (Page {a.source.page})")
                            for a in total_amounts
                        ],
                        status="REVIEW_REQUIRED",
                        description="Mâu thuẫn giữa các giá trị tổng số tiền được trích xuất trong cùng một tài liệu."
                    )
                )

        # 2. Math check (if subtotal + vat != total amount)
        net_amt_facts = [f for f in facts if f.fact_type == "NET_AMOUNT"]
        exempt_amt_facts = [f for f in facts if f.fact_type == "TAX_EXEMPT_SUBTOTAL"]
        vat_amt_facts = [f for f in facts if f.fact_type == "VAT_AMOUNT"]
        tot_amt_fact = next((f for f in facts if f.fact_type in ["TOTAL_AMOUNT", "GROSS_AMOUNT"]), None)

        if (net_amt_facts or exempt_amt_facts) and tot_amt_fact:
            try:
                sum_net = sum(float(f.value) for f in net_amt_facts if isinstance(f.value, (int, float)))
                sum_exempt = sum(float(f.value) for f in exempt_amt_facts if isinstance(f.value, (int, float)))
                sum_vat = sum(float(f.value) for f in vat_amt_facts if isinstance(f.value, (int, float)))
                tot = float(tot_amt_fact.value)
                
                # NET_AMOUNT (Cộng tiền hàng) already incorporates non-taxable / exempt subtotals.
                # Do not double-count sum_exempt if sum_net is present.
                if sum_net > 0:
                    calc_total = sum_net + sum_vat
                else:
                    calc_total = sum_exempt + sum_vat

                # Check if calc_total matches tot (try combinations for multi-tax rate subtotals)
                matches_math = (
                    abs(calc_total - tot) <= 10.0 or
                    abs((sum_net + sum_exempt + sum_vat) - tot) <= 10.0 or
                    any(abs((sum_net + float(v.value)) - tot) <= 10.0 for v in vat_amt_facts if isinstance(v.value, (int, float))) or
                    any(abs((sum_exempt + float(v.value)) - tot) <= 10.0 for v in vat_amt_facts if isinstance(v.value, (int, float)))
                )
                
                if not matches_math:
                    conflicts.append(
                        ConflictItem(
                            field="amount",
                            values=[
                                ConflictValue(value=tot, source=f"Fact {tot_amt_fact.evidence_fact_id} (Total)"),
                                ConflictValue(value=calc_total, source=f"Sum of Net ({sum_net}) + VAT ({sum_vat})")
                            ],
                            status="REVIEW_REQUIRED",
                            description="Tổng tiền thanh toán không khớp với Tổng cộng tiền hàng + Tiền thuế GTGT."
                        )
                    )
            except (ValueError, TypeError):
                pass

        # 2.5. Check conflict between TABLE_SUM_AMOUNT and TOTAL_AMOUNT / NET_AMOUNT
        table_sum_fact = next((f for f in facts if f.fact_type == "TABLE_SUM_AMOUNT"), None)
        if table_sum_fact and tot_amt_fact:
            try:
                table_sum = float(table_sum_fact.value)
                tot = float(tot_amt_fact.value)
                net_facts = [f for f in facts if f.fact_type == "NET_AMOUNT"]
                net_val = float(net_facts[0].value) if net_facts and isinstance(net_facts[0].value, (int, float)) else None

                # Cho phép khớp với TOTAL_AMOUNT hoặc NET_AMOUNT (trước thuế)
                matches_table_math = (
                    abs(table_sum - tot) <= 10.0 or 
                    (net_val is not None and abs(table_sum - net_val) <= 10.0)
                )
                # Chỉ cảnh báo nếu chênh lệch đáng kể (> 1000 VND)
                if not matches_table_math and abs(table_sum - tot) > 1000.0:
                    conflicts.append(
                        ConflictItem(
                            field="table_sum",
                            values=[
                                ConflictValue(value=table_sum, source=f"Fact {table_sum_fact.evidence_fact_id} (Tổng các dòng bảng)"),
                                ConflictValue(value=tot, source=f"Fact {tot_amt_fact.evidence_fact_id} (Tổng tiền thanh toán)")
                            ],
                            status="REVIEW_REQUIRED",
                            description=f"Tổng số tiền các dòng trong bảng ({table_sum:,.0f}) không khớp với Tổng tiền thanh toán ({tot:,.0f})."
                        )
                    )
            except (ValueError, TypeError):
                pass

        # 3. Check for conflict with related document facts (e.g. Contract vs Invoice amount)
        if related_facts:
            rel_amounts = [f for f in related_facts if f.fact_type in ["TOTAL_AMOUNT", "GROSS_AMOUNT", "AMOUNT"]]
            if total_amounts and rel_amounts:
                doc_amt = float(total_amounts[0].value) if isinstance(total_amounts[0].value, (int, float)) else None
                rel_amt = float(rel_amounts[0].value) if isinstance(rel_amounts[0].value, (int, float)) else None

                if doc_amt and rel_amt and abs(doc_amt - rel_amt) > 0.01:
                    conflicts.append(
                        ConflictItem(
                            field="amount",
                            values=[
                                ConflictValue(value=doc_amt, source=f"Doc {total_amounts[0].source.document_id}"),
                                ConflictValue(value=rel_amt, source=f"Doc {rel_amounts[0].source.document_id}")
                            ],
                            status="REVIEW_REQUIRED",
                            description="Mâu thuẫn số tiền giữa tài liệu này và tài liệu liên quan."
                        )
                    )

        # 4. Check for party name conflict
        def normalize_party(val: Any) -> str:
            if not val:
                return ""
            s = str(val).lower().strip()
            s = re.sub(
                r'^(?:ký bởi|ký bởi\:|tên đơn vị bán|tên đơn vị mua|đơn vị bán|đơn vị mua|bên bán|bên mua|bên chuyển nhượng|bên nhận chuyển nhượng|người mua hàng|người bán hàng|bên a|bên b|seller|buyer|payer|payee|tài khoản nhận|số tài khoản nhận|tên người nhận|tên người chuyển|tài khoản trích nợ|tài khoản chuyển|ngân hàng nhận|ngân hàng chuyển|hình thức chuyển|hình thức thanh toán|nội dung chuyển tiền|nội dung|lời nhắn|lưu mẫu)[\:\s\-]*',
                '',
                s
            )
            s = re.sub(r'[\s\-]+ngân hàng(?:\s+nhận|\s+chuyển)?.*$', '', s)
            s = re.sub(r'[^\w\s]', '', s)
            return re.sub(r'\s+', ' ', s).strip()

        # Check for conflicts within specific role categories (Payer conflicts vs Payee conflicts)
        def check_role_conflicts(role_facts: List[EvidenceFact], role_name: str):
            if len(role_facts) < 2:
                return
            p_map = {}
            for p in role_facts:
                norm = normalize_party(p.value)
                if norm and len(norm) > 3:
                    if norm not in p_map:
                        p_map[norm] = p

            sorted_norms = sorted(p_map.keys(), key=len, reverse=True)
            filtered_map = {}
            for norm in sorted_norms:
                if not any(norm in longer for longer in filtered_map.keys()):
                    filtered_map[norm] = p_map[norm]

            if len(filtered_map) >= 2:
                conflicts.append(
                    ConflictItem(
                        field="party",
                        values=[
                            ConflictValue(value=p.value, source=f"Fact {p.evidence_fact_id}")
                            for p in filtered_map.values()
                        ],
                        status="REVIEW_REQUIRED",
                        description=f"Mâu thuẫn giữa các giá trị {role_name} trong cùng tài liệu."
                    )
                )

        payers = [f for f in facts if f.fact_type == "PAYER"]
        payees = [f for f in facts if f.fact_type == "PAYEE"]
        check_role_conflicts(payers, "Bên mua / Bên chuyển (Payer)")
        check_role_conflicts(payees, "Bên bán / Bên nhận (Payee)")

        # Overall party count check only for unrolled general PARTY facts
        general_parties = [f for f in facts if f.fact_type == "PARTY"]
        if not conflicts and len(general_parties) >= 3:
            p_map = {}
            for p in general_parties:
                norm = normalize_party(p.value)
                if norm and len(norm) > 3:
                    if norm not in p_map:
                        p_map[norm] = p

            sorted_norms = sorted(p_map.keys(), key=len, reverse=True)
            filtered_p_map = {}
            for norm in sorted_norms:
                if not any(norm in longer for longer in filtered_p_map.keys()):
                    filtered_p_map[norm] = p_map[norm]

            if len(filtered_p_map) > 2:  # More than 2 distinct non-overlapping parties
                conflicts.append(
                    ConflictItem(
                        field="party",
                        values=[
                            ConflictValue(value=p.value, source=f"Fact {p.evidence_fact_id}")
                            for p in filtered_p_map.values()
                        ],
                        status="REVIEW_REQUIRED",
                        description="Nhiều tên đơn vị đối tác không khớp nhau trong cùng tài liệu."
                    )
                )

        return conflicts
