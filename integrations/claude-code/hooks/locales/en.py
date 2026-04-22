"""English locale patterns for the Hewn classifier.

This is the default locale. It loads unconditionally — every other locale
is additive on top of it.
"""
from __future__ import annotations


IR_RULES: list[tuple[str, int]] = [
    (r"\bdebug(?:ging)?\b|\bdiagnose\b|\broot[- ]cause\b|\btrace(?:s|d)?\b.*(?:bug|error|outage|failure)|\boutage\b", 3),
    # "why does X fail/break/crash/error" — diagnostic question
    (r"\bwhy\s+(?:does|is|are|do|did)\b.*(?:fail|break|crash|error|bug|wrong|broken|flaky|intermittent)", 3),
    (r"\breview\b.*(?:code|diff|patch|pr|commit|architecture|design|module|service)", 3),
    (r"\baudit\b.*(?:code|security|auth|module|api|implementation)", 3),
    (r"\bcritique\b|\banalyz[e|ing]\b.*(?:consistency|risk|tradeoff|failure)", 3),
    (r"\bfix\b.*(?:bug|code|race|issue|vulnerabilit|defect|regression|leak)|\bresolve\b.*(?:bug|issue|race)", 3),
    (r"\brefactor\b|\bre-?design\b", 2),
    (r"\bdesign\b.*(?:architecture|schema|pattern|saga|state[- ]machine|migration|split|boundary|flow)", 3),
    (r"\bpropose\b.*(?:fix|architecture|split|schema|mitigation|boundary|ownership|pattern|structure)", 3),
    (r"\bdescribe\b.*(?:target|architecture|fix|state[- ]machine|consistency|flow|protocol|boundary)", 2),
    (r"\bvulnerabilit|bypass.*(?:auth|security|signature)|signature[- ]forger|algo[- ]confus|jwt.*(?:none|algo|implementation|decode|verify)|\brace[- ]condition\b|\bdeadlock\b|\binjection\b|\bexploit\b|\battack[- ]vector", 3),
    (r"\bsecurity\s+issues?\b|\bexploitabilit|rank\s+by\s+severity|\bforged?\s+signature\b", 3),
    (r"\bwhich\b.*(?:slo|metric|alert|canary|dashboard|gauge|signal)|\bwhat\b.*(?:metric|alert|canary|threshold|slo)", 3),
    (r"\bconsistency\b.*(?:window|bound|model|guarantee|violat)|eventual.*consist", 2),
    (r"```|\bdef\s+\w+\s*\(|\bclass\s+\w+\b|diff --git|^[+-][^-+]", 2),
    (r"\bwhat\s+(?:is\s+)?(?:wrong|the\s+bug|the\s+issue|the\s+problem|the\s+attack)\b", 3),
    # Technical Q&A can safely use compact IR. Explanations aimed at juniors,
    # tutorials, or non-technical readers stay prose via PROSE_RULES below.
    (r"\bexplain\b.*\b(?:database|db|connection\s+pool(?:ing)?|pooling|sql|cors|tcp|udp|hash\s+table|debounc\w*|git|rebase|merge|queue|topic|messaging|react|component|browser|node\.?js|memory\s+leak)\b", 2),
    (r"\bhow\s+(?:does|do|is|are|should)\b.*\b(?:database|db|connection\s+pool(?:ing)?|pooling|sql|cors|tcp|udp|hash\s+table|collisions?|debounc\w*|git|rebase|merge|queue|topic|messaging|react|component|browser|node\.?js|memory\s+leak)\b", 2),
    (r"\bwhy\s+(?:does|do|is|are|am|are|did)\b.*\b(?:re-?render|render|cors|error|sql|tcp|udp|hash\s+table|debounc\w*|git|rebase|merge|queue|topic|messaging|react|component|browser|node\.?js|memory\s+leak)\b", 2),
    (r"\bwhat(?:'s|\s+is)\s+(?:the\s+)?(?:difference|diff|point)\b.*\b(?:tcp|udp|sql|cors|hash\s+table|debounc\w*|git|rebase|merge|queue|topic|messaging|react|component|browser|node\.?js|database|db)\b", 2),
    (r"\bwhat\s+does\b.*\b(?:sql|explain|command|cors|tcp|udp|git|rebase|merge|queue|topic|hash\s+table|debounc\w*|database|db)\b", 2),
    (r"\b(?:differ|differs|vs\.?|versus)\b.*\b(?:tcp|udp|git|rebase|merge|queue|topic|messaging|sql|database|db)\b", 2),
    (r"\bwhen\s+should\s+i\s+use\b.*\b(?:queue|topic|messaging|tcp|udp|git|rebase|merge|sql|database|db)\b", 2),
    (r"\brepro(?:duce|duction)?\b.*(?:test|case|script)|\bregression\s+tests?\b", 2),
    # Bare "propose/hypothesis" gets low weight (1) — needs to stack with
    # another IR signal to cross threshold. The specific weight-3 propose
    # pattern above already catches "propose the fix/architecture/etc".
    # Weight 1 here avoids false positives on "propose 5 names/noms/nomi".
    (r"\bpropose\b|\bhypothe[sz]iz|\bhypothesis\b", 1),
    (r"\bsaga\b|\btwo[- ]?phase[- ]?commit\b|\b2pc\b|\bidempot|\bcompensat\w*|\bprojection\b", 2),
    (r"\bwalk[- ]through\b.*(?:trace|log|stack|error)|\bwhat\s+the\s+trace\b", 3),
    (r"\b(?:audit|analy[sz]e|analy[sz]ing|study|inspect|examine|assess|evaluate)\s+(?:this\s+)?(?:repo|repository|dir(?:ectory)?|code[- ]?base|project|module|impl\w*)\b", 3),
    (r"\bwhat(?:'s|\s+is)\s+(?:missing|fragile|solid|broken|wrong|risky)\b", 2),
]

PROSE_RULES: list[tuple[str, int]] = [
    (r"\bnon[- ]technical\b|\bstakeholders?\b|\bleadership\b|\bexecutive\b|\bc[- ]suite\b|\bcustomer[- ]facing\b", 5),
    (r"\bmemo\b|\bnarrative\b|\bessay\b|\bparagraph\b|\bbullet[- ]free\b|\bno\s+bullet\b|\bin\s+prose\b|\bno\s+markdown\b|\bno\s+code\b,?\s*no\s+ir", 4),
    (r"\bexplain\b.*(?:junior|beginner|newcomer|non[- ]tech|five\s+year|like.*im)|\btutorial\b|\bwalkthrough\b.*(?:how|works|beginner)", 3),
    (r"\bbrainstorm\b|\bthink\s+out\s+loud\b|\bdiscussion\b", 3),
    (r"\bpost[- ]?mortem\b.*(?:write|draft|compose|customer|blameless)|\bretrospective\b.*(?:write|narrative|reflective)", 4),
    (r"\brfc\b.*(?:draft|write|compose)|\bdesign[- ]doc\b|\bone[- ]pager\b.*(?:leader|exec)", 3),
    (r"\breadable\b|\bprofessional\s+tone\b|\breassuring\b|\btone:\s*(?:blameless|professional|reflective|narrative)", 2),
    (r"\bno\s+ir\b|\bno\s+hewn\b|\bno\s+flint\b", 5),
]

FINDINGS_RULES: list[str] = [
    r"\b(?:top|first|main|biggest|highest[- ]impact|most\s+(?:likely|severe|critical|important|dangerous|common|worst))\s+(?:\d+|few|several|many)?\s*(?:\w+\s+)?(?:bugs?|issues?|risks?|problems?|findings?|gaps?|vulnerabilit(?:y|ies)|failures?|failure\s+modes?|blockers?|footguns?)\b",
    r"\b(?:which|what)\s+(?:are\s+|is\s+)?(?:the\s+)?(?:\d+|few|top|main|biggest|most\s+(?:likely|severe|critical|important|dangerous|common))\s+(?:\w+\s+)?(?:bugs?|issues?|risks?|problems?|findings?|gaps?|vulnerabilit(?:y|ies)|failures?|failure\s+modes?|blockers?|footguns?)\b",
    r"\b(?:which|what)\s+(?:bugs?|issues?|problems?|failures?|risks?|footguns?)\s+(?:would|will|could|might|may)\s+(?:a\s+)?(?:users?|devs?|developers?|people)?\s*(?:encounter|hit|experience|face|meet)\b",
    r"\b(?:find|identify|list|flag)\s+(?:every|all|top|\d+|the\s+main|the\s+most\s+likely)?\s*(?:the\s+)?(?:security\s+)?(?:issues?|vulnerabilit(?:y|ies)|risks?|bugs?|findings?|failure\s+modes?|blockers?|footguns?)\b.*\b(?:rank|severity|probability|likelihood|impact|evidence|file:line)\b",
    r"\b(?:rank|prioriti[sz]e)\b.*\b(?:bugs?|issues?|risks?|vulnerabilit(?:y|ies)|findings?|blockers?|footguns?)\b.*\b(?:severity|risk|impact|probability|likelihood)\b",
    r"\b(?:launch|ship|release)\s+blockers?\b|\bfootguns?\b|\bfailure\s+modes?\b",
]

CODE_ARTIFACT_RULES: list[str] = [
    r"\b(?:show|display|produce|emit|provide)\s+(?:me\s+)?(?:the\s+|a\s+|an\s+)?(?:updated|full|complete|new|final)\s+(?:code|file|method|function|class|module|source|impl\w*)",
    r"\b(?:show|display)\s+(?:me\s+)?(?:the\s+|a\s+|an\s+)?(?:updated\s+)?(?:code|config|patch|diff|snippet)",
    r"\bwrite\s+(?:me\s+)?(?:the\s+|a\s+|an\s+)?(?:code|tests?|snippet|function|method|patch|fix|script|implementation|regression\s+tests?|pytest|unit\s+tests?)",
    r"\bimplement\s+(?:the|a|an)\b",
    r"\bapply\s+the\s+(?:fix|change|patch|update)",
    r"\b(?:include|with)\s+(?:the\s+)?(?:sample|example|inline|exact|updated|actual|full)\s+(?:\w+\s+){0,3}?(?:code|config|snippet|patch|diff|script)\b",
    r"\b(?:include|with)\s+(?:the\s+)?(?:code|config|snippet|patch|diff|script)\b",
    r"\b(?:code|config|snippet|patch|diff|script)\s+(?:\w+\s+){0,4}?\binline\b",
    r"\bsample\s+(?:code|config|snippet)\b",
    r"\bupdated\s+(?:\w+\.\w+|jwt_\w+|auth\w*|handler|service|module|file)",
    r"\bpropose\s+the\s+fix.*(?:show|code|snippet|file)",
]

POLISHED_AUDIENCE_RULES: list[str] = [
    r"\bleadership\b|\bnon[- ]technical\b|\bstakeholders?\b|\bexecutive\b|\bc[- ]suite\b",
    r"\bcustomer[- ]facing\b|\bcustomer[- ]?(?:memo|letter|update|announcement)\b",
    r"\bmemo\b.*(?:leadership|stakeholder|customer)|\bdraft\s+a\s+(?:memo|letter|announcement)",
    r"\bpost[- ]?mortem\b.*(?:customer|blameless|public|external)",
    r"\bprofessional\s+tone\b|\bblameless\s+tone\b|\breassuring\b",
    r"\b(?:2|3|4|5|two|three|four|five)\s+paragraphs?\b",
]
