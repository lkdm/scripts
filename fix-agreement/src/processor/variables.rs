use regex::Regex;

pub fn remove_xml_in_variables(buf: &str) -> String {
    // Regular expression to match content between pipes `|...|`
    let re = Regex::new(r"\|([^|]*)\|").unwrap();

    // If no matches found, return the original string
    if !re.is_match(buf) {
        return buf.to_string();
    }

    // Replace each matched variable content with cleaned content
    let result = re.replace_all(buf, |caps: &regex::Captures| {
        let var_content = caps.get(1).map_or("", |m| m.as_str());
        let cleaned = remove_xml_in_variable_content(var_content);
        format!("|{}|", cleaned) // Keep the pipes but clean the content inside
    });

    result.to_string() // Convert result back to a String before returning
}

/// Function to remove XML tags within a variable content (between pipes)
fn remove_xml_in_variable_content(content: &str) -> String {
    // Remove XML tags (using non-greedy match to allow nested tags)
    let re = Regex::new(r"<[^>]+>").unwrap(); // Match XML tags (any opening and closing)
    re.replace_all(content, "").to_string() // Replace all tags with an empty string
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_remove_xml_in_variables_basic() {
        let input = "<tag1><tag2>some text |var1| |var<badxmltag />2|</tag2></tag1>";
        let expected = "<tag1><tag2>some text |var1| |var2|</tag2></tag1>";
        let result = remove_xml_in_variables(input);
        assert_eq!(result, expected);
    }

    #[test]
    fn test_remove_xml_in_variables_no_variables() {
        let input = "<tag1><tag2>no variables here</tag2></tag1>";
        let expected = "<tag1><tag2>no variables here</tag2></tag1>";
        let result = remove_xml_in_variables(input);
        assert_eq!(result, expected);
    }

    #[test]
    fn test_remove_xml_in_variables_single_variable() {
        let input = "<tag><tag2>Text with |var<badtag />| and more</tag2></tag>";
        let expected = "<tag><tag2>Text with |var| and more</tag2></tag>";
        let result = remove_xml_in_variables(input);
        assert_eq!(result, expected);
    }

    #[test]
    fn test_remove_xml_in_variables_multiple_variables() {
        let input = "<tag><tag2>Text with |var1| and |var<selfclosing />2| and |var3|</tag2></tag>";
        let expected = "<tag><tag2>Text with |var1| and |var2| and |var3|</tag2></tag>";
        let result = remove_xml_in_variables(input);
        assert_eq!(result, expected);
    }

    #[test]
    fn test_remove_xml_in_variables_empty() {
        let input = "<tag><tag2>Text with |var|</tag2></tag>";
        let expected = "<tag><tag2>Text with |var|</tag2></tag>";
        let result = remove_xml_in_variables(input);
        assert_eq!(result, expected);
    }

    #[test]
    fn test_remove_xml_in_variables_no_xml_inside_variables() {
        let input = "<tag><tag2>Text with |simplevar| and more text</tag2></tag>";
        let expected = "<tag><tag2>Text with |simplevar| and more text</tag2></tag>";
        let result = remove_xml_in_variables(input);
        assert_eq!(result, expected);
    }

    #[test]
    fn test_remove_xml_in_variables_only_xml_tags() {
        let input = "<tag><tag2><selfclosing /> |<badxmltag />var|</tag2></tag>";
        let expected = "<tag><tag2><selfclosing /> |var|</tag2></tag>";
        let result = remove_xml_in_variables(input);
        assert_eq!(result, expected);
    }

    #[test]
    fn test_remove_xml_in_variables_multiple_pipes() {
        let input = "Text with |var1| and |var<innertag />2| and more |var3| here";
        let expected = "Text with |var1| and |var2| and more |var3| here";
        let result = remove_xml_in_variables(input);
        assert_eq!(result, expected);
    }

    #[test]
    fn test_remove_xml_in_variables_with_surrounding_xml() {
        let input = "<tag><tag2>Text with <style>|simplevar|</style> and more text</tag2></tag>";
        let expected = "<tag><tag2>Text with <style>|simplevar|</style> and more text</tag2></tag>";
        let result = remove_xml_in_variables(input);
        assert_eq!(result, expected);
    }
}
