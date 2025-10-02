use std::{borrow::Cow, fs, path::Path};

use quick_xml::{Reader, events::Event};
use regex::Regex;

use crate::processor::variables::remove_xml_in_variables;
pub mod variables;

pub struct DocumentProcessor {
    highlight_variables: bool,
    set_variable_size: Option<u8>,
    left_align_variable_cells: bool,
    unlock_regions: bool,
}

impl DocumentProcessor {
    pub fn process(
        &self,
        input_path: &Path,
        output_path: &Path,
    ) -> Result<(), Box<dyn std::error::Error>> {
        let content = fs::read_to_string(input_path)?;
        let variable_regex = Regex::new(r"\|[^|]+\|")?;

        let mut reader = Reader::from_str(&content);
        reader.config_mut().trim_text(true);

        // // Process the XML content
        let mut count = 0;
        let mut txt = Vec::new();
        let mut buf = Vec::new();
        //
        // for event in reader.events() {}

        loop {
            match reader.read_event_into(&mut buf) {
                Err(e) => panic!("Error at position {}: {:?}", reader.error_position(), e),
                Ok(Event::Eof) => break,
                // Ok(Event::Start(e)) => match e.name().as_ref() {},
                // Ok(Event::End(e) => )
                Ok(Event::Text(e)) => {
                    let text = e.decode().unwrap().into_owned();
                    // Clean the text inside variables (between pipes)
                    let cleaned_text = remove_xml_in_variables(&text);
                    txt.push(cleaned_text);
                }
                _ => (),
            }
            buf.clear();
        }

        // Join the cleaned text into a single string
        let output_content = txt.join("\n");

        // Write the cleaned content to the output file
        fs::write(output_path, output_content)?;

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{fs, io, path::Path};
    use tempfile::tempdir;

    fn process_tester(
        input: &str,
        processor: &DocumentProcessor,
    ) -> Result<String, Box<dyn std::error::Error>> {
        let dir = tempdir()?; // Automatically handles cleanup of the temp directory
        let input_path = dir.path().join("input.xml");
        let output_path = dir.path().join("output.xml");

        // Write the input to the temporary file
        fs::write(&input_path, input)?;

        // Process the file
        processor.process(&input_path, &output_path)?;

        // Check if output file exists before reading
        if !output_path.exists() {
            eprintln!("Output file not found: {:?}", output_path);
            return Err(Box::new(io::Error::new(
                io::ErrorKind::NotFound,
                "Output file missing",
            )));
        }

        // Read the output from the temporary file
        let result = fs::read_to_string(output_path)?;

        Ok(result)
    }

    #[test]
    fn test_processor_keep_variables_intact() {
        let input = r#"
    <table:table-row>
     <table:table-cell table:style-name="Table1.A2" office:value-type="string">
      <text:p text:style-name="P1">|VariableName|</text:p>
     </table:table-cell>
    </table:table-row>
        "#;
        let expected = r#"
    <table:table-row>
     <table:table-cell table:style-name="Table1.A2" office:value-type="string">
      <text:p text:style-name="P1">|VariableName|</text:p>
     </table:table-cell>
    </table:table-row>
        "#;
        let processor = DocumentProcessor {
            highlight_variables: false,
            set_variable_size: None,
            left_align_variable_cells: false,
            unlock_regions: false,
        };

        let result = process_tester(input, &processor).unwrap();
        assert_eq!(result, expected);
    }

    #[test]
    fn test_processor_remove_xml_inside_variables() {
        let input = r#"
    <table:table-row>
     <table:table-cell table:style-name="Table1.A2" office:value-type="string">
      <text:p text:style-name="P1">|Var<myxml>iable</myxml>Name|</text:p>
     </table:table-cell>
    </table:table-row>
        "#;
        let expected = r#"
    <table:table-row>
     <table:table-cell table:style-name="Table1.A2" office:value-type="string">
      <text:p text:style-name="P1">|VariableName|</text:p>
     </table:table-cell>
    </table:table-row>
        "#;
        let processor = DocumentProcessor {
            highlight_variables: false,
            set_variable_size: None,
            left_align_variable_cells: false,
            unlock_regions: false,
        };

        let result = process_tester(input, &processor).unwrap();
        assert_eq!(result, expected);
    }
}
