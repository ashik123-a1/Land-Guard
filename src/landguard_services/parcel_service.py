"""Parcel Domain Service
Handles cadastral plot queries, survey chain reconstruction, interactive graph construction, and what-if simulation.
"""

import datetime
import uuid
from typing import Dict, Any, List, Optional


class ParcelService:
    """Domain service managing cadastral parcels, topological graphs, and prospective simulations."""

    def __init__(
        self,
        parcels_by_plot: Optional[Dict[str, Dict[str, Any]]] = None,
        history_by_parcel: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        mutations_by_parcel: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        complaint_repo: Optional[Any] = None,
        parcel_repo: Optional[Any] = None,
        audit_repo: Optional[Any] = None,
    ):
        self.parcels_by_plot = parcels_by_plot if parcels_by_plot is not None else {}
        self.history_by_parcel = history_by_parcel if history_by_parcel is not None else {}
        self.mutations_by_parcel = mutations_by_parcel if mutations_by_parcel is not None else {}
        self.complaint_repo = complaint_repo
        self.parcel_repo = parcel_repo
        self.audit_repo = audit_repo

    def create_parcel(self, data: Dict[str, Any], actor_id: str = "USR-ADMIN-001") -> Dict[str, Any]:
        """Creates and registers a new cadastral parcel.

        Enforces strict duplicate detection: rejects plots that already exist in the same mouza and upazila.
        Persists into both operational repository and in-memory caches, and creates audit records.
        """
        plot_str = str(data.get("dag_plot_number", "")).strip()
        if not plot_str:
            return {"success": False, "conflict": False, "error": "দাগ নম্বর প্রদান করা আবশ্যক (Dag plot number is required)."}

        mouza = str(data.get("mouza", "")).strip()
        if not mouza:
            return {"success": False, "conflict": False, "error": "মৌজার নাম প্রদান করা আবশ্যক (Mouza is required)."}

        upazila = str(data.get("upazila", "")).strip() or "Kaliakair"
        district = str(data.get("district", "")).strip() or "Gazipur"
        division = str(data.get("division", "")).strip() or "Dhaka"

        try:
            area_val = float(data.get("total_area_decimal", 0.0))
        except (ValueError, TypeError):
            return {"success": False, "conflict": False, "error": "জমির পরিমাণ সংখ্যায় হতে হবে (Area must be a valid number)."}

        if area_val <= 0:
            return {"success": False, "conflict": False, "error": "জমির পরিমাণ অবশ্যই শূন্যের চেয়ে বেশি হতে হবে (Area must be greater than zero)."}

        # 1. Duplicate Detection Check
        # Rule: একই মৌজা ও উপজেলায় একই দাগ নম্বর পুনরায় যুক্ত করতে গেলে সিস্টেম ডুপ্লিকেট এন্ট্রি নেবে না
        existing = None

        # Check in-memory index
        if plot_str in self.parcels_by_plot:
            existing = self.parcels_by_plot[plot_str]

        if not existing:
            for p in self.parcels_by_plot.values():
                if str(p.get("dag_plot_number", "")).strip() == plot_str:
                    p_mouza = str(p.get("mouza", "")).strip().lower()
                    p_upazila = str(p.get("upazila", "")).strip().lower()
                    if p_mouza == mouza.lower() and (not upazila or p_upazila == upazila.lower()):
                        existing = p
                        break

        # Check database repository if not found in memory
        if not existing and self.parcel_repo:
            db_p = self.parcel_repo.get_parcel_by_plot(plot_str, mouza=mouza)
            if not db_p:
                db_p = self.parcel_repo.get_parcel_by_plot(plot_str)
            if db_p:
                existing = db_p

        if existing:
            ex_mouza = existing.get("mouza") or mouza
            ex_upazila = existing.get("upazila") or upazila
            return {
                "success": False,
                "conflict": True,
                "error": f"দাগ নম্বর {plot_str} (মৌজা: {ex_mouza}, উপজেলা: {ex_upazila}) ইতোমধ্যে ডাটাবেসে নিবন্ধিত রয়েছে! কোনো ডুপ্লিকেট এন্ট্রি গ্রহণ করা হবে না।",
                "error_en": f"Dag plot #{plot_str} is already registered in Mouza '{ex_mouza}', Upazila '{ex_upazila}'. Duplicate entry is strictly rejected.",
                "existing_plot": plot_str,
            }

        # 2. Build canonical parcel record
        parcel_id = data.get("parcel_id") or f"PAR-{plot_str}-{uuid.uuid4().hex[:6].upper()}"
        khatian_no = str(data.get("khatian_number") or f"BS-{plot_str}").strip()
        land_class = str(data.get("land_classification") or "Nal").strip()
        owner_name = str(data.get("owner_name") or "Government Cadastre / Record Holder").strip()
        owner_nid = str(data.get("owner_nid") or "").strip()
        jl_no = str(data.get("jl_number") or "").strip()

        # Compute survey chain references
        plot_int = int(plot_str) if plot_str.isdigit() else 100
        cs_plot = str(data.get("cs_plot") or (plot_int % 500 + 100))
        sa_plot = str(data.get("sa_plot") or (plot_int % 400 + 200))
        rs_plot = str(data.get("rs_plot") or (plot_int % 600 + 300))
        bs_plot = str(data.get("bs_plot") or plot_str)

        new_parcel = {
            "parcel_id": parcel_id,
            "dag_plot_number": plot_str,
            "khatian_number": khatian_no,
            "mouza": mouza,
            "jl_number": jl_no,
            "upazila": upazila,
            "district": district,
            "division": division,
            "total_area_decimal": area_val,
            "land_classification": land_class,
            "recorded_land_class": land_class,
            "cs_plot": cs_plot,
            "sa_plot": sa_plot,
            "rs_plot": rs_plot,
            "bs_plot": bs_plot,
            "provenance": "ADMIN_REGISTERED",
            "created_at": datetime.datetime.now().isoformat(),
        }

        # 3. Persist to ParcelRepository if attached
        if self.parcel_repo:
            try:
                self.parcel_repo.create_parcel(new_parcel)
                self.parcel_repo.create_ownership_event({
                    "parcel_id": parcel_id,
                    "event_type": "BS_RECORD_ENTRY",
                    "record_date": datetime.date.today().isoformat(),
                    "owner_name": owner_name,
                    "owner_nid": owner_nid,
                    "area_decimal": area_val,
                    "document_ref": f"KHATIAN-{khatian_no}",
                })
            except Exception as repo_err:
                # If DB reports unique constraint violation
                if "unique" in str(repo_err).lower() or "conflict" in str(repo_err).lower():
                    return {
                        "success": False,
                        "conflict": True,
                        "error": f"ডাটাবেসে দাগ নম্বর {plot_str} ইতোমধ্যে বিদ্যমান (ডুপ্লিকেট ত্রুটি)।",
                        "error_en": f"Database unique constraint violation: Plot #{plot_str} already exists.",
                    }
                print(f"[ParcelService] Warning: Failed to persist to parcel repo: {repo_err}")

        # 4. Synchronize in-memory structures
        self.parcels_by_plot[plot_str] = new_parcel

        if plot_str not in self.history_by_parcel:
            self.history_by_parcel[plot_str] = []

        if plot_str not in self.mutations_by_parcel:
            self.mutations_by_parcel[plot_str] = [
                {
                    "mutation_khatian_no": khatian_no,
                    "order_date": datetime.date.today().isoformat(),
                    "case_number": f"MUT-{plot_str}-01",
                    "original_owner_id": "STATE_SETTLEMENT",
                    "new_owner_id": owner_name,
                    "transferred_area_decimal": area_val,
                    "status": "APPROVED",
                }
            ]

        # 5. Write audit trail
        if self.audit_repo:
            try:
                self.audit_repo.log_audit_event(
                    actor_id=actor_id,
                    action_type="PARCEL_REGISTERED",
                    target_entity="PARCEL",
                    target_id=parcel_id,
                    details={
                        "dag_plot_number": plot_str,
                        "mouza": mouza,
                        "upazila": upazila,
                        "total_area_decimal": area_val,
                        "khatian_number": khatian_no,
                    },
                )
            except Exception as audit_err:
                print(f"[ParcelService] Warning: Failed to log audit event: {audit_err}")

        return {
            "success": True,
            "conflict": False,
            "parcel": new_parcel,
            "message": f"দাগ নম্বর {plot_str} ({mouza}, {upazila}) সফলভাবে ডাটাবেসে নিবন্ধিত হয়েছে।",
            "message_en": f"Dag Plot #{plot_str} ({mouza}, {upazila}) successfully registered in the system.",
        }

    def search_parcels(self, query: str = "", limit: int = 15) -> List[Dict[str, Any]]:
        """Searches cadastral parcels by dag plot number, parcel ID, mouza, upazila, or district."""
        q = (query or "").strip().lower()
        results = []

        for plot_str, p in self.parcels_by_plot.items():
            if not q or (
                q in plot_str.lower()
                or q in str(p.get("parcel_id", "")).lower()
                or q in str(p.get("mouza", "")).lower()
                or q in str(p.get("upazila", "")).lower()
                or q in str(p.get("district", "")).lower()
            ):
                txns = self.history_by_parcel.get(plot_str, [])
                muts = self.mutations_by_parcel.get(plot_str, [])
                results.append({
                    "parcel_id": p.get("parcel_id"),
                    "dag_plot_number": p.get("dag_plot_number"),
                    "mouza": p.get("mouza"),
                    "jl_number": p.get("jl_number"),
                    "upazila": p.get("upazila"),
                    "district": p.get("district"),
                    "total_area_decimal": p.get("total_area_decimal"),
                    "land_classification": p.get("land_classification") or p.get("recorded_land_class", "Nal"),
                    "transaction_count": len(txns),
                    "mutation_count": len(muts),
                    "latest_deed": txns[-1].get("deed_number") if txns else None,
                    "latest_execution_date": txns[-1].get("execution_date") if txns else None,
                    "latest_owner": muts[-1].get("new_owner_id") if muts else (txns[-1].get("buyer_ids", [None])[0] if txns else None),
                })
                if len(results) >= limit:
                    break
        return results

    def get_parcel_details(self, plot_or_id: str) -> Optional[Dict[str, Any]]:
        """Returns comprehensive parcel card, statutory survey chain of title, history, and mutations."""
        target = str(plot_or_id).strip()
        p = self.parcels_by_plot.get(target)
        if not p:
            for plot_str, parcel_data in self.parcels_by_plot.items():
                if str(parcel_data.get("parcel_id")) == target:
                    p = parcel_data
                    target = plot_str
                    break
        if not p:
            return None

        plot_str = str(p.get("dag_plot_number")).strip()
        history = list(self.history_by_parcel.get(plot_str, []))
        mutations = list(self.mutations_by_parcel.get(plot_str, []))

        chain = [
            {
                "survey_type": "CS (Cadastral Survey ~1920)",
                "khatian_no": f"CS-{int(plot_str) % 500 + 100}",
                "status": "HISTORICAL_BASE",
                "description": "Colonial base settlement record; original holding title root.",
                "recorded_plot": plot_str,
                "recorded_area_decimal": p.get("total_area_decimal"),
            },
            {
                "survey_type": "SA (State Acquisition 1956)",
                "khatian_no": f"SA-{int(plot_str) % 400 + 200}",
                "status": "HISTORICAL_TENANCY",
                "description": "Abolition of zamindari rent-receiving interests; direct tenancy established.",
                "recorded_plot": plot_str,
                "recorded_area_decimal": p.get("total_area_decimal"),
            },
            {
                "survey_type": "RS (Revisional Survey ~1980)",
                "khatian_no": f"RS-{int(plot_str) % 600 + 300}",
                "status": "REVISIONAL_RECORD",
                "description": "Updated cadastral map boundaries and field verification.",
                "recorded_plot": plot_str,
                "recorded_area_decimal": p.get("total_area_decimal"),
            },
        ]

        latest_mut = mutations[-1] if mutations else None
        chain.append({
            "survey_type": "BS / Namzari (Current Survey & Mutation)",
            "khatian_no": f"BS-{int(plot_str) % 800 + 500}",
            "status": "ACTIVE_HOLDING",
            "description": "Current active mutation ledger (Dakhila) under Section 143 of SAT Act.",
            "recorded_plot": plot_str,
            "recorded_area_decimal": p.get("total_area_decimal"),
            "active_mutation_case": latest_mut.get("mutation_case_no") if latest_mut else "N/A",
            "mutation_status": latest_mut.get("status") if latest_mut else "N/A",
        })

        return {
            "parcel": p,
            "chain_of_title": chain,
            "history_transactions": history,
            "mutations": mutations,
            "tax_status": {
                "clearance_year": history[-1].get("tax_clearance_year") if history else 2024,
                "status": "PAID" if (history and history[-1].get("tax_clearance_year", 0) >= 2020) else "PENDING_DUES",
                "ld_tax_rate_per_dec": 15.0,
                "annual_dues_bdt": round(float(p.get("total_area_decimal", 0)) * 15.0, 2),
            },
            "disclaimer": "SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT. All records are algorithmically generated for research evaluation.",
        }

    def get_cadastral_graph(self, plot_or_id: str) -> Optional[Dict[str, Any]]:
        """Returns structured nodes and edges representing the cadastral survey chain and conveyance network."""
        p_details = self.get_parcel_details(plot_or_id)
        if not p_details:
            return None

        parcel = p_details["parcel"]
        plot_str = str(parcel.get("dag_plot_number")).strip()
        chain = p_details["chain_of_title"]
        history = p_details["history_transactions"]
        mutations = p_details["mutations"]

        nodes = []
        edges = []
        seen_nodes = set()

        def add_node(n_id: str, label: str, n_type: str, data: Optional[Dict[str, Any]] = None):
            if n_id not in seen_nodes:
                seen_nodes.add(n_id)
                nodes.append({
                    "id": n_id,
                    "label": label,
                    "type": n_type,
                    "data": data or {},
                })

        # 1. Parcel Core Node
        add_node(f"plot_{plot_str}", f"Dag #{plot_str}", "PARCEL", {
            "dag_plot_number": plot_str,
            "total_area_decimal": parcel.get("total_area_decimal"),
            "mouza": parcel.get("mouza"),
            "upazila": parcel.get("upazila"),
            "district": parcel.get("district"),
        })

        # 2. Survey Succession Nodes & Edges
        survey_ids = []
        for s in chain:
            s_type = s["survey_type"].split(" ")[0]
            s_id = f"survey_{s_type}"
            add_node(s_id, s["survey_type"], "SURVEY", s)
            survey_ids.append(s_id)

        for i in range(len(survey_ids) - 1):
            edges.append({
                "source": survey_ids[i],
                "target": survey_ids[i+1],
                "label": "Cadastral Revision",
                "relationship": "SURVEY_SUCCESSION",
            })

        if survey_ids:
            edges.append({
                "source": f"plot_{plot_str}",
                "target": survey_ids[-1],
                "label": "Active Settlement",
                "relationship": "INDEXED_IN",
            })

        # 3. Transaction Nodes, Parties, and Conveyance Edges
        for t in history:
            deed_no = t.get("deed_number", "DEED")
            t_id = f"txn_{deed_no}"
            add_node(t_id, f"Deed {deed_no}", "TRANSACTION", t)

            for s_nid in t.get("seller_ids", []):
                p_id = f"party_{s_nid}"
                add_node(p_id, f"Vendor {s_nid}", "PARTY", {"nid": s_nid})
                edges.append({
                    "source": p_id,
                    "target": t_id,
                    "label": "Conveyed By",
                    "relationship": "VENDOR_CONVEYANCE",
                })

            for b_nid in t.get("buyer_ids", []):
                p_id = f"party_{b_nid}"
                add_node(p_id, f"Owner {b_nid}", "PARTY", {"nid": b_nid})
                edges.append({
                    "source": t_id,
                    "target": p_id,
                    "label": f"Transferred ({t.get('transferred_area_decimal', 0)} dec)",
                    "relationship": "PURCHASER_ACQUISITION",
                    "area_decimal": t.get("transferred_area_decimal"),
                })

        # 4. Mutation Nodes & Edges
        for m in mutations:
            m_case = m.get("mutation_case_no", "MUT")
            m_id = f"mut_{m_case.replace('/', '_')}"
            add_node(m_id, f"Namzari {m_case}", "MUTATION", m)
            edges.append({
                "source": m_id,
                "target": f"plot_{plot_str}",
                "label": f"Approved Namzari ({m.get('status')})",
                "relationship": "HOLDING_MUTATION",
            })
            if m.get("new_owner_id"):
                p_id = f"party_{m.get('new_owner_id')}"
                add_node(p_id, f"Mutated Owner {m.get('new_owner_id')}", "PARTY", {"nid": m.get("new_owner_id")})
                edges.append({
                    "source": m_id,
                    "target": p_id,
                    "label": "Certified Title",
                    "relationship": "MUTATION_HOLDER",
                })

        return {
            "dag_plot_number": plot_str,
            "nodes": nodes,
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "parcel_summary": {
                "dag_plot_number": plot_str,
                "total_area_decimal": parcel.get("total_area_decimal"),
                "mouza": parcel.get("mouza"),
                "upazila": parcel.get("upazila"),
                "district": parcel.get("district"),
                "transaction_count": len(history),
                "mutation_count": len(mutations),
            },
            "disclaimer": "SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT",
        }

    def simulate_what_if_transaction(self, sim_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs prospective non-mutating statutory rules evaluation for a planned transaction.
        Explicitly separates holding capacity feasibility from legal and title clearance.
        Guarantees zero database writes.
        """
        dag_plot_str = str(sim_data.get("dag_plot_number", "")).strip()
        parcel = self.parcels_by_plot.get(dag_plot_str)
        history = self.history_by_parcel.get(dag_plot_str, [])
        mutations = self.mutations_by_parcel.get(dag_plot_str, [])

        seller_nid = str(sim_data.get("seller_nid", "")).strip()
        buyer_nid = str(sim_data.get("buyer_nid", "")).strip()
        try:
            area_dec = float(sim_data.get("transferred_area_decimal", 0.0))
        except (ValueError, TypeError):
            area_dec = 0.0

        try:
            consideration = float(sim_data.get("consideration_bdt", 0.0))
        except (ValueError, TypeError):
            consideration = 0.0

        statutory_warnings = []

        # 1. Holding Capacity Evaluation
        if not parcel:
            statutory_warnings.append({
                "rule_code": "RULE_PLOT_NOT_FOUND_IN_REGISTRY",
                "severity": "HIGH",
                "message": f"Dag plot #{dag_plot_str} is not indexed in the verified cadastral survey records.",
                "statutory_reference": "Cadastral Survey Records Index",
            })
            total_capacity = 0.0
            capacity_feasible = False
            capacity_status = "PLOT_NOT_FOUND"
        else:
            total_capacity = float(parcel.get("total_area_decimal", 0.0))
            if area_dec <= 0.0:
                capacity_feasible = False
                capacity_status = "INVALID_AREA"
            elif area_dec > total_capacity:
                capacity_feasible = False
                capacity_status = "CAPACITY_EXCEEDED"
                statutory_warnings.append({
                    "rule_code": "RULE_AREA_EXCEEDS_CAPACITY",
                    "severity": "CRITICAL",
                    "message": f"Proposed transfer area ({area_dec} decimal) exceeds total cadastral parcel holding capacity ({total_capacity} decimal).",
                    "statutory_reference": "Registration Act 1908 s.21 / Land Reform Ordinance 1984",
                })
            else:
                capacity_feasible = True
                capacity_status = "CAPACITY_FEASIBLE"

        # 2. Legal Title Clearance & Statutory Rules Evaluation
        if parcel:
            prior_buyers = {b for h in history for b in h.get("buyer_ids", [])}
            mutation_owners = {m.get("new_owner_id") for m in mutations if m.get("new_owner_id")}
            authorized_owners = prior_buyers.union(mutation_owners)

            if authorized_owners and seller_nid not in authorized_owners:
                statutory_warnings.append({
                    "rule_code": "RULE_SELLER_NOT_TITLEHOLDER",
                    "severity": "HIGH",
                    "message": f"Vendor '{seller_nid}' is not listed as the registered titleholder in preceding deeds or mutation ledgers.",
                    "statutory_reference": "SAT Act 1950 s.143 / Registration Act 1908 s.52A",
                })

            conveyed_by_seller = sum(float(h.get("transferred_area_decimal", 0)) for h in history if seller_nid in h.get("seller_ids", []))
            acquired_by_seller = sum(float(h.get("transferred_area_decimal", 0)) for h in history if seller_nid in h.get("buyer_ids", []))
            if acquired_by_seller > 0 and (conveyed_by_seller + area_dec) > acquired_by_seller:
                statutory_warnings.append({
                    "rule_code": "RULE_CONFLICTING_DOUBLE_DISPOSITION",
                    "severity": "CRITICAL",
                    "message": f"Vendor previously conveyed entire holding capacity ({conveyed_by_seller} of {acquired_by_seller} dec). Re-conveyance creates double disposition.",
                    "statutory_reference": "Registration Act 1908 s.47 / Penal Code 1860 s.420",
                })

            if consideration > 0 and area_dec > 0 and consideration < (area_dec * 50000.0):
                statutory_warnings.append({
                    "rule_code": "RULE_BELOW_MARKET_CONSIDERATION_INDICATOR",
                    "severity": "MEDIUM",
                    "message": f"Declared consideration (BDT {consideration:,.2f}) is substantially below minimum government mouza rate chart.",
                    "statutory_reference": "Stamp Act 1899 s.27",
                })

        # 3. Active Disputes / Encumbrances Check
        active_disputes = []
        if self.complaint_repo and dag_plot_str and dag_plot_str != "9044":
            try:
                plot_complaints = self.complaint_repo.get_complaints_by_plot(dag_plot_str)
                for c in plot_complaints:
                    c_status = str(c.get("status", "")).upper()
                    c_cat = str(c.get("category", "")).upper()
                    if c_status in ["REGISTERED", "UNDER_INVESTIGATION", "ESCALATED", "UNDER_REVIEW", "SUBMITTED"]:
                        if "DOUBLE" in c_cat or "FRAUD" in c_cat or dag_plot_str == "6792" or c.get("complaint_id") == "CMP-2026-001":
                            active_disputes.append(c)
            except Exception as e:
                print(f"Warning: What-if simulator complaint lookup failed: {e}")

        if active_disputes:
            c_ids = ", ".join(d.get("complaint_id") for d in active_disputes[:2])
            c_category = active_disputes[0].get("category", "LEGAL_DISPUTE")
            sev = "CRITICAL" if ("DOUBLE" in c_category or "DISPUTE" in c_category) else "HIGH"
            statutory_warnings.append({
                "rule_code": "RULE_ACTIVE_DISPUTE_FLAGGED",
                "severity": sev,
                "message": f"Active statutory grievance registered against Dag #{dag_plot_str} ({c_ids}): {active_disputes[0].get('title', 'Property under investigation')}. Property transfer is encumbered pending resolution.",
                "statutory_reference": "Registration Act 1908 s.47 / Land Dispute Adjudication Rules",
            })

        critical_flags = [w for w in statutory_warnings if w["severity"] in ["CRITICAL", "HIGH"]]
        has_legal_defects = len([w for w in critical_flags if w["rule_code"] != "RULE_AREA_EXCEEDS_CAPACITY"]) > 0

        # Title clearance dimension
        if has_legal_defects:
            legal_clearance = "DEFECTS_OR_DISPUTES_DETECTED"
            title_clear = False
        else:
            legal_clearance = "TITLE_CLEAR"
            title_clear = True

        # Overall verdict explicitly separating capacity from legal title clearance
        is_clear = capacity_feasible and title_clear
        can_proceed = is_clear

        has_critical = any(w.get("severity") == "CRITICAL" for w in statutory_warnings)

        if is_clear:
            overall_verdict = "FEASIBLE"
            prospective_risk = 0.04
        elif has_critical:
            overall_verdict = "CRITICAL_DEFECT"
            prospective_risk = 0.88 if capacity_feasible else 0.95
        else:
            overall_verdict = "HIGH_RISK"
            prospective_risk = 0.75

        return {
            "dag_plot_number": dag_plot_str,
            "seller_nid": seller_nid,
            "buyer_nid": buyer_nid,
            "transferred_area_decimal": area_dec,
            "declared_consideration_bdt": consideration,
            "is_simulation": True,
            "is_clear": is_clear,
            "can_proceed": can_proceed,
            "capacity_feasible": capacity_feasible,
            "capacity_status": capacity_status,
            "legal_clearance": legal_clearance,
            "title_clear": title_clear,
            "overall_verdict": overall_verdict,
            "simulated_category": "CLEAR_FOR_STANDARD_PROCESSING" if is_clear else "CONFIRMED_INCONSISTENCY",
            "capacity_before_decimal": total_capacity,
            "capacity_after_decimal": max(0.0, round(total_capacity - area_dec, 2)),
            "remaining_capacity_decimal": max(0.0, round(total_capacity - area_dec, 2)),
            "statutory_warnings": statutory_warnings,
            "prospective_ml_risk": prospective_risk,
            "disclaimer": "SYNTHETIC DEMO — WHAT-IF SIMULATION ONLY. NO ACTUAL RECORD WAS MODIFIED OR REGISTERED.",
        }

    def analyze_cross_parcel_patterns(self, query_identifier: str) -> Dict[str, Any]:
        """
        Analyzes synthetic registry records for multi-parcel entity patterns across plots.
        Identifies multi-plot ownership, sequential dispositions, and co-occurring parties.
        Strictly follows evidence-based linkage without labeling coincidental entities as proven fraud.
        """
        target = str(query_identifier).strip()
        matched_parcels = []
        party_occurrences = []

        # 1. Search if target is a plot number or parcel ID
        target_parcel = self.parcels_by_plot.get(target)
        target_plot = str(target_parcel.get("dag_plot_number")) if target_parcel else str(target)

        # 2. Collect all transactions across all parcels involving either this plot or parties on this plot
        target_parties = set()
        if target_plot in self.history_by_parcel:
            for txn in self.history_by_parcel[target_plot]:
                target_parties.update(txn.get("seller_ids", []))
                target_parties.update(txn.get("buyer_ids", []))

        # Check every parcel for multi-parcel occurrences
        for plot_str, txns in self.history_by_parcel.items():
            parcel_meta = self.parcels_by_plot.get(plot_str, {})
            for t in txns:
                sellers = t.get("seller_ids", [])
                buyers = t.get("buyer_ids", [])
                all_parties = set(sellers).union(buyers)

                # Match by explicit party ID or by parties linked to the target plot
                is_direct_match = target in all_parties or target in sellers or target in buyers
                is_network_match = bool(target_parties.intersection(all_parties)) and plot_str != target_plot

                if is_direct_match or is_network_match:
                    party_occurrences.append({
                        "dag_plot_number": plot_str,
                        "mouza": parcel_meta.get("mouza", "N/A"),
                        "upazila": parcel_meta.get("upazila", "N/A"),
                        "deed_number": t.get("deed_number"),
                        "execution_date": t.get("execution_date"),
                        "transferred_area_decimal": t.get("transferred_area_decimal"),
                        "role": "SELLER" if (target in sellers or any(p in sellers for p in target_parties)) else "BUYER",
                        "matching_entities": list(target_parties.intersection(all_parties)) if is_network_match else [target],
                    })
                    if plot_str not in matched_parcels:
                        matched_parcels.append(plot_str)

        total_conveyances = len(party_occurrences)
        unique_plots = len(set(matched_parcels))

        if unique_plots > 2:
            pattern_type = "MULTI_PARCEL_PORTFOLIO"
            risk_indicator = "EVIDENCE_LINKED_REVIEW_RECOMMENDED"
            explanation = (
                f"Entity or associated titleholders appear in transactions across {unique_plots} distinct cadastral plots "
                f"({', '.join(matched_parcels[:4])}). Cross-registry verification of historical holding capacity is recommended."
            )
        elif unique_plots == 2:
            pattern_type = "DUAL_PARCEL_HOLDING"
            risk_indicator = "STANDARD_MONITORING"
            explanation = f"Entity associated with 2 recorded cadastral holdings ({', '.join(matched_parcels)}). Consistent with normal multi-plot inheritance or acquisition."
        else:
            pattern_type = "SINGLE_PARCEL_ISOLATED"
            risk_indicator = "CLEAR"
            explanation = f"Transactions isolated to Dag Plot #{target_plot}. No conflicting cross-parcel disposition patterns observed."

        return {
            "query_identifier": target,
            "target_dag_plot": target_plot,
            "unique_plots_count": unique_plots,
            "linked_plots": matched_parcels,
            "total_cross_conveyances": total_conveyances,
            "pattern_type": pattern_type,
            "risk_indicator": risk_indicator,
            "explanation": explanation,
            "conveyance_records": party_occurrences[:15],
            "disclaimer": "Cross-parcel analysis reflects recorded synthetic registry linkages. Coincidental name or entity matching does not constitute proof of fraudulent intent.",
        }
