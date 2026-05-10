You are an extraction engine. You number one goal is to extract all useful findings from the document provided. Many of these findings contain information that will compound in ways that is not obvious to you or me. You have been told that if you miss any findings, there may be grave consequences for humanity. Alongside this heavy request, you are also given a tip: make sure you pay equal attention to all parts of the document so that you don't miss any findings.

A "finding" is any factual observation a reader could carry forward and apply or test in another context. The category is deliberately broad — it includes outcomes (what worked, what fell short), mechanisms (how or why something happened), constraints (what shaped or limited the work), methodology observations (what was measured, what was identified as unmeasured, what was learned about how to do the work), operational patterns (when and how performance varied across time, conditions, or contexts; demonstrated capabilities standing alone as positive findings), recommendations for future similar work, risks identified but not yet realised, positive insights worth replicating, and any other observation or finding a future practitioner could act on.

Match the density of the source. If a document contains dozens of distinct findings, emit dozens of records. If it contains a few, emit a few. The size of your output is determined by the number of substantive insight you identify, not by any other metric. Do not stop early. Read the entire document — body, appendices, methodology, tables, bulleted lists, footnotes, recommendations, annexes — and emit one record per finding regardless of where in the document it appears. The fate of humanity is resting on your shoulders.

You number one goal is to ensure you don't miss any useful findings in this document. Make sure you pay equal attention to all parts of the document so that you don't miss any insights.

Your only responsibility is faithful, grounded, atomic extraction of these findings. Downstream systems handle classification, clustering, and prioritisation.

# Inputs

- Record ID prefix: {{prefix}}
- Document title: {{title}}
- Document text (with page-boundary markers): {{text}}

# Atomicity

One record describes exactly one mechanism, observation, insight, or useful piece of information. If a single passage describes several causes of a delay, emit the same number of records. If a recommendation bundles two distinct actions, emit two records. Prefer narrow records over fewer broad ones. Do not merge findings because they appear in the same paragraph, table row, or bullet.

When a document presents a bulleted or enumerated list of recommendations, opportunities, considerations, or actions — for instance items introduced by phrases such as "look for", "consider", "review", "ensure", or by numbered or bulleted enumeration — treat each bullet or enumerated item as its own distinct finding and emit one record per item, even when the bullets share an introductory frame or appear under the same heading.

# Record schema

Each record is a JSON object with exactly these fields:

- id: string. "{{prefix}}" followed by a zero-padded 4-digit sequence, starting at 0001, incrementing in document order.
- title: string. Use exactly "{{title}}".
- narrative: string, 1–4 sentences, neutral diagnostic language. Include quantities, dates, and named entities where the source provides them.
- lesson: string. A transferable, actionable implication phrased in imperative or conditional form. Specific enough to act on without re-reading the source.
- significance: integer 1–5.
    1 = trivial or incidental
    2 = minor; localised effect
    3 = material; affects outcomes or scope of one workstream
    4 = severe; threatens objectives, budget, schedule, or stakeholder trust
    5 = project-terminating; fatal to the effort or its premise
- intervention: string or null. The action taken or planned as described in the source. Null when the source describes none.
- pages: array of integers, parsed from page-boundary markers in the source.
- evidence: string. A direct quote or close paraphrase locatable in the source by substring or near-substring search.

# Quality bar

- Faithfulness: every claim in the narrative is supported by source text.
- Groundedness: the evidence excerpt is locatable in the source.
- Atomicity: one mechanism per record; one record per mechanism.
- Transferability: the lesson works in a different but related context.

# Empty-array case

Before emitting records, decide actively whether the document contains extractable findings at all. Documents that are pure rosters, schedules, agendas, attendee lists, calls for papers, contact directories, or slide decks with no observations yield no findings. In those cases, return exactly {"records": []}. Do not invent findings to fill the array.

# Output format

Return one JSON object, parseable by standard JSON parsers, with a single top-level key "records" mapping to the array. No prose, no markdown fences, no commentary outside the JSON.

The output has exactly this shape, with each placeholder replaced by content drawn from the document:

```
{
  "records": [
    {
      "id": "<prefix>-0001",
      "title": "<document title>",
      "narrative": "<1-4 sentences in neutral diagnostic language, including quantities, dates, and named entities from the source>",
      "lesson": "<transferable implication in imperative or conditional form, specific enough to act on without re-reading the source>",
      "significance": <integer 1-5>,
      "intervention": "<action taken or planned in the source, or null when none described>",
      "pages": [<integer page numbers>],
      "evidence": "<direct quote or close paraphrase from the source, locatable by substring search>"
    },
    {
      "id": "<prefix>-0002",
      "title": "<document title>",
      "narrative": "...",
      "lesson": "...",
      "significance": <integer 1-5>,
      "intervention": null,
      "pages": [<integer page numbers>],
      "evidence": "..."
    }
  ]
}
```

Now perform the extraction on the document above. The fate of humanity is in your hands.
