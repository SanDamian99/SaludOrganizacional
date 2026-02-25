class ResponseRouter:
    """
    Determina el pathway correcto antes de llamar a Gemini.
    """
    
    def route(self, user_question: str, available_data: dict) -> str:
        """
        Returns: "direct_answer" | "data_insufficient" | "out_of_scope" | 
                 "needs_clarification" | "sensitive_topic"
        """
        question = user_question.lower()
        
        # Sensitive Topic Check
        crisis_keywords = ['suicidio', 'matar', 'depresion clinica', 'ansiedad severa', 'autolesion', 'morir', 'daño']
        if any(kw in question for kw in crisis_keywords):
            return "sensitive_topic"
            
        # Out of Scope (Individual identification)
        individual_keywords = ['quien', 'nombre', 'correo', 'especifico', 'fulano', 'pedro', 'maria']
        if any(kw in question for kw in individual_keywords) and ('peor' in question or 'mejor' in question or 'puntaje' in question):
            return "out_of_scope"
            
        # Clarification
        ambiguous = ['esto', 'aquello', 'eso', 'malo', 'bueno']
        
        # Check if the sentence has less than or exactly 3 words and contains an ambiguous keyword, 
        # or if it's literally just the ambiguous keywords.
        words = question.split()
        if len(words) <= 3 and any(kw in words for kw in ambiguous):
            return "needs_clarification"

        # Check existing dimensions in data vs question
        # If available_data specifies dimensions, check overlap
        if available_data and 'columns' in available_data:
            cols_lower = [c.lower() for c in available_data['columns']]
            # Basic matching to ensure we have SOME data they ask about if it's related to study
            # Alternatively, if we detect they ask about a dimension completely absent
            study_keywords = ['agotamiento', 'burnout', 'estres', 'liderazgo', 'apoyo', 'acoso', 'engagement']
            asked_about_study = any(kw in question for kw in study_keywords)
            
            # Very naive check for data insufficient
            if asked_about_study:
                found_match = any(kw in c for c in cols_lower for kw in study_keywords if kw in question)
                if not found_match and 'burnaut' not in question: # tolerate typos
                    return "data_insufficient"

        return "direct_answer"
