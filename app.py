import streamlit as st
import json
import re

# --------------------------------
# 1. Mappings and Helper Functions
# --------------------------------

language_map = {
    "dutch": "nl",
    "german": "de",
    "italian": "it",
    "japanese": "ja",
    "korean": "ko",
    "polish": "pl",
    "portuguese": "pt",
    "russian": "ru",
    "spanish": "es",
    "turkish": "tr",
    "french": "fr",
    "fr": "fr",
    "english": "en",
}

# This dictionary maps each technical “issue code” to a user-friendly description:
FRIENDLY_ISSUE_DESCRIPTIONS = {
    "missing_start_space": (
        "The reference text begins with a space, but the translation does not. "
        "Please add a space at the beginning if it's necessary."
    ),
    "missing_end_space": (
        "The reference text ends with a space, but the translation does not. "
        "Please add a space at the end if it's necessary."
    ),
    "missing_start_line_break": (
        "The reference text begins with a newline, but the translation does not. "
        "Please add a line break at the start if required."
    ),
    "missing_end_line_break": (
        "The reference text ends with a newline, but the translation does not. "
        "Please add a line break at the end if required."
    ),
    "wrong_line_break_count": (
        "The total number of line breaks differs between reference and translation. "
        "If multiple lines are intended, please ensure they match."
    ),
    "missing_end_dot": (
        "The reference text ends with a period ('.'), but the translation does not. "
        "Consider adding it for consistency unless punctuation is not required."
    ),
    "extra_end_dot": (
        "The reference text does not end with a period ('.'), but the translation does. "
        "Consider removing the final period for consistency."
    )
}

def detect_language_code(file_name):
    """
    Looks for a known language name in the file name.
    Returns a short code like 'en', 'es', etc., or None if no match.
    """
    lower_name = file_name.lower()
    for lang, code in language_map.items():
        if lang in lower_name:
            return code
    return None

def extract_params(text):
    """
    Finds placeholders in curly braces, e.g., {name}, returning them as a set.
    """
    matches = re.findall(r"{(\w+)}", text)
    return set(matches)

def check_text_issues(source, target, lang_code):
    """
    Checks for formatting differences: spaces, line breaks, final period, etc.
    Returns a list of 'issue codes'.
    """
    issues = []

    # Leading/trailing space checks
    if source.startswith(" ") and not target.startswith(" "):
        issues.append("missing_start_space")
    if source.endswith(" ") and not target.endswith(" "):
        issues.append("missing_end_space")

    # Leading/trailing newline checks
    if source.startswith("\n") and not target.startswith("\n"):
        issues.append("missing_start_line_break")
    if source.endswith("\n") and not target.endswith("\n"):
        issues.append("missing_end_line_break")

    # Compare line-break count
    if source.count("\n") != target.count("\n"):
        issues.append("wrong_line_break_count")

    # Check final dot, except for Japanese
    if lang_code != "ja":
        if source.endswith(".") and not target.endswith("."):
            issues.append("missing_end_dot")
        elif not source.endswith(".") and target.endswith("."):
            issues.append("extra_end_dot")

    return issues

def compare_arb_files(reference_data, target_data, target_file_name):
    """
    Compares reference ARB data vs. target ARB data and returns details:
      - Missing/extra keys
      - Empty translations
      - Identical translations
      - Parameter / text issues
    """
    ref_keys = [k for k in reference_data.keys() if not k.startswith("@")]
    tgt_keys = [k for k in target_data.keys() if not k.startswith("@")]

    missing_keys = [k for k in ref_keys if k not in tgt_keys]
    extra_keys = [k for k in tgt_keys if k not in ref_keys]

    empty_translations = []
    identical_translations = []
    parameter_issues = []

    lang_code = detect_language_code(target_file_name) or "unknown"

    # Compare only keys that exist in both
    for key in ref_keys:
        if key not in tgt_keys:
            continue

        ref_val = reference_data[key]
        tgt_val = target_data[key]

        # Check empty
        if not isinstance(ref_val, str) or not isinstance(tgt_val, str):
            continue
        ref_val = ref_val.strip()
        tgt_val = tgt_val.strip()

        # Check empty
        if not tgt_val:
            empty_translations.append(key)
        elif ref_val == tgt_val:
            identical_translations.append(key)

        # Check parameters
        ref_params = extract_params(ref_val)
        tgt_params = extract_params(tgt_val)
        missing_params = [p for p in ref_params if p not in tgt_params]
        extra_params = [p for p in tgt_params if p not in ref_params]

        # Check text/format issues
        text_issues = check_text_issues(ref_val, tgt_val, lang_code)

        if missing_params or extra_params or text_issues:
            parameter_issues.append({
                "key": key,
                "reference": ref_val,
                "target": tgt_val,
                "missingParams": missing_params,
                "extraParams": extra_params,
                "textIssues": text_issues
            })

    return {
        "langCode": lang_code,
        "missingKeys": missing_keys,
        "extraKeys": extra_keys,
        "emptyTranslations": empty_translations,
        "identicalTranslations": identical_translations,
        "parameterIssues": parameter_issues,
    }


# --------------------------------
# 2. STREAMLIT APP
# --------------------------------

def main():
    st.title("ARB File Comparison Tool")
    st.write(
        "Upload a **reference ARB** file (for example, the original in English) "
        "and a **target ARB** file (the translation). This tool will detect "
        "common issues like missing keys, empty translations, parameter mismatches, "
        "and spacing/formatting differences."
    )

    ref_file = st.file_uploader("Reference ARB File", type=["arb"])
    tgt_file = st.file_uploader("Target ARB File", type=["arb"])

    if ref_file and tgt_file:
        if st.button("Compare ARB Files"):
            try:
                reference_data = json.load(ref_file)
                target_data = json.load(tgt_file)

                results = compare_arb_files(reference_data, target_data, tgt_file.name)

                st.subheader("Comparison Results")

                # Language code
                st.write(f"**Detected Language Code:** {results['langCode']}")

                # Missing keys
                if results["missingKeys"]:
                    with st.expander("Missing Keys"):
                        st.write(
                            "These keys exist in the reference file but are **not** "
                            "present in the target file."
                        )
                        st.write(results["missingKeys"])
                else:
                    st.success("No missing keys found.")

                # Extra keys
                if results["extraKeys"]:
                    with st.expander("Extra Keys"):
                        st.write(
                            "These keys exist in the target file but are **not** "
                            "present in the reference file."
                        )
                        st.write(results["extraKeys"])
                else:
                    st.success("No extra keys found.")

                # Empty translations
                if results["emptyTranslations"]:
                    with st.expander("Empty Translations"):
                        st.write(
                            "These keys have **empty** translations. "
                            "Please add the correct text or confirm if they're intentionally empty."
                        )
                        st.write(results["emptyTranslations"])
                else:
                    st.success("No empty translations found.")

                # Identical translations
                if results["identicalTranslations"]:
                    st.warning("Some translations are identical to the reference.")
                    with st.expander("Identical Translations"):
                        st.write(
                            "The following keys have translations exactly the same as the reference."
                            "\nIf this is intentional (e.g., brand names), ignore this warning."
                        )
                        st.write(results["identicalTranslations"])
                else:
                    st.success("No identical translations found.")

                # Parameter and text issues
                if results["parameterIssues"]:
                    st.warning("Some entries have parameter or formatting issues.")
                    for issue in results["parameterIssues"]:
                        with st.expander(f"Key: {issue['key']}"):
                            st.markdown(
                                f"**Reference text:**\n```\n{issue['reference']}\n```"
                            )
                            st.markdown(
                                f"**Target text:**\n```\n{issue['target']}\n```"
                            )

                            # Missing params
                            if issue["missingParams"]:
                                st.error(
                                    "Missing placeholders in the target:\n"
                                    f"{issue['missingParams']}\n\n"
                                    "Please ensure these parameters are included, "
                                    "e.g., {example}."
                                )
                            # Extra params
                            if issue["extraParams"]:
                                st.error(
                                    "Unexpected placeholders in the target:\n"
                                    f"{issue['extraParams']}\n\n"
                                    "If they are not needed, please remove them."
                                )

                            # Text issues
                            if issue["textIssues"]:
                                st.error("Text Issues Detected:")
                                for code in issue["textIssues"]:
                                    description = FRIENDLY_ISSUE_DESCRIPTIONS.get(
                                        code,
                                        f"Unknown issue: {code}"
                                    )
                                    st.write(f"• **{code}**: {description}")
                else:
                    st.success("No parameter or formatting issues found.")

            except Exception as e:
                st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
