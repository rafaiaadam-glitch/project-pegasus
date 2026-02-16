def generate_artifacts_with_llm(
    transcript: str,
    preset_id: str,
    course_id: str,
    lecture_id: str,
    generated_at: str | None = None,
    # UPDATED: Use 'gemini-3-pro-preview' for Vertex AI alignment
    model: str = "gemini-3-pro-preview", 
    thread_refs: List[str] | None = None,
    provider: str = "gemini",
) -> Dict[str, Dict[str, Any]]:
    if generated_at is None:
        generated_at = _iso_now()

    # Load preset configuration
    preset_config = _load_preset_config(preset_id)
    if preset_config:
        print(f"[LLM Generation] Using preset: {preset_config.get('name', preset_id)}")
    else:
        print(f"[LLM Generation] WARNING: Could not load preset config for {preset_id}, using defaults")

    # Build customized prompt
    prompt = _build_generation_prompt(preset_id, preset_config)
    user_content = f"Preset: {preset_id}\nTranscript:\n{transcript}"

    provider_key = provider.strip().lower()
    raw_text = ""

    if provider_key == "openai":
        payload = {
            "model": model,
            "input": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_content},
            ],
            "response_format": {"type": "json_object"},
        }
        response = _request_openai(payload)
        raw_text = _extract_openai_text(response)

    elif provider_key in {"gemini", "vertex"}:
        try:
            # 1. Initialize Vertex AI
            # FORCE location='global' for Gemini 3 preview models to avoid 404s
            project_id = os.getenv("GCP_PROJECT_ID", "delta-student-486911-n5")
            vertexai.init(project=project_id, location="global") 

            # 2. Instantiate Model
            generative_model = GenerativeModel(model)
            print(f"[LLM Generation] Generating via Vertex AI model: {model}")

            # 3. Generate Content with Thinking Mode enabled via parameters
            response = generative_model.generate_content(
                [prompt, user_content],
                generation_config=GenerationConfig(
                    response_mime_type="application/json",
                    # Enable the reasoning chain via parameters
                    thinking_level="HIGH", 
                    # Google recommends 1.0 for reasoning tasks
                    temperature=1.0         
                )
            )
            raw_text = response.text

        except Exception as e:
            print(f"[LLM Generation] Vertex AI Error: {e}")
            raise RuntimeError(f"Vertex AI generation failed: {e}")
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        print(f"[LLM Generation] JSON Decode Error. Raw output:\n{raw_text[:200]}...")
        raise ValueError(f"LLM failed to return valid JSON: {e}")

    mapping = {
        "summary": "summary",
        "outline": "outline",
        "key_terms": "key-terms",
        "flashcards": "flashcards",
        "exam_questions": "exam-questions",
    }

    artifacts: Dict[str, Dict[str, Any]] = {}
    for key, artifact_type in mapping.items():
        if key not in data:
            print(f"[LLM Generation] Warning: Missing '{key}' in LLM response.")
            continue

        artifact = data[key]
        if not isinstance(artifact, dict):
            print(f"[LLM Generation] Warning: Artifact '{key}' is not an object.")
            continue

        base = _base_artifact(
            artifact_type=artifact_type,
            course_id=course_id,
            lecture_id=lecture_id,
            preset_id=preset_id,
            generated_at=generated_at,
        )

        base.update(artifact)
        base["artifactType"] = artifact_type

        if thread_refs:
            base["threadRefs"] = thread_refs

        artifacts[artifact_type] = base

    return artifacts
