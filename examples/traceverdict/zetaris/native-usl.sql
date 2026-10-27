CREATE NAMESPACE IF NOT EXISTS lightning.metastore;

CREATE NAMESPACE IF NOT EXISTS lightning.metastore.traceverdict;

ACTIVATE USL TABLE lightning.metastore.traceverdict.cases.case_evidence AS SELECT u.tenant_id,u.agent_id,u.case_id,u.evidence_kind,u.evidence_json FROM (
 SELECT tenant_id,agent_id,case_id,evidence_kind,evidence_json FROM tv_events.evidence
 UNION ALL SELECT tenant_id,agent_id,case_id,evidence_kind,evidence_json FROM tv_configuration.evidence
 UNION ALL SELECT tenant_id,agent_id,case_id,evidence_kind,evidence_json FROM tv_reference.evidence
) u
JOIN tv_events.case_membership e ON u.tenant_id=e.tenant_id AND u.agent_id=e.agent_id AND u.case_id=e.case_id
JOIN tv_configuration.case_membership c ON u.tenant_id=c.tenant_id AND u.agent_id=c.agent_id AND u.case_id=c.case_id
JOIN tv_reference.case_membership r ON u.tenant_id=r.tenant_id AND u.agent_id=r.agent_id AND u.case_id=r.case_id;

LIST DQ USL lightning.metastore.traceverdict.cases;

RUN DQ valid_evidence_payload TABLE lightning.metastore.traceverdict.cases.case_evidence;

SELECT evidence_kind,COUNT(*) AS records FROM lightning.metastore.traceverdict.cases.case_evidence GROUP BY evidence_kind;

CREATE OR REPLACE SCHEMASTORE VIEW case_evidence WITH CONTAINER traceverdict AS SELECT tenant_id,agent_id,case_id,evidence_kind,evidence_json FROM lightning.metastore.traceverdict.cases.case_evidence