import logging
from app.services.model_service import ModelService
from app.utils.file import PartFile
import os
import re
logger = logging.getLogger("uvicorn.error")

class ExtractReprocessService:

    def __init__(self, model_service: ModelService, file: PartFile):
        self.model_service = model_service
        self.file = file

    async def reprocess(self, gemini_response: str):
        """
        Logic to reprocess the extract. 
        Handles two cases: 
        1. JSON cut off during "movements" 
        2. JSON cut off during "trusts"
        """
        if gemini_response is None:
            logger.warning("gemini_response is None")
            return None
        
        clean = ExtractReprocessService.clean_str(gemini_response)
        if clean is None:
            logger.warning("clean is None")
            return None


        # Determine which list was being processed when the cut occurred
        cut_context = self.determine_cut_context(clean)
        logger.info(f"Determined cut context: {cut_context}")

        if cut_context == "movimientos":
            # Find last complete movement in movements
            value = self.find_last_complete_movement(clean,"value")
            subsequentBalance = self.find_last_complete_movement(clean,"subsequentBalance")
            logger.info(f"Found movimientos context - value: {value}, subsequentBalance: {subsequentBalance}")

            # Check if movimientos array is empty (just opened)
            is_empty_movimientos = self._is_empty_movimientos_array(clean)
            
            if (value and subsequentBalance) or is_empty_movimientos:
                if is_empty_movimientos:
                    logger.info("Reprocessing movimientos from beginning - empty array detected")
                    prompt_with_context = self.read_movimientos_prompt_without_context()
                else:
                    logger.info(f"Reprocessing movimientos from: value{value}, subsequentBalance{subsequentBalance}")
                    prompt_with_context = self.read_movimientos_prompt_with_context(value, subsequentBalance)
                
                mres = await self.model_service.make_prompt_with_file(prompt_with_context, self.file.part)
                res = mres.text.strip()
                
                # Remove markdown code block formatting if present
                if res.startswith('```json'):
                    res = res[7:]  # Remove ```json
                elif res.startswith('```'):
                    res = res[3:]   # Remove ```
                
                if res.endswith('```'):
                    res = res[:-3]  # Remove trailing ```
                
                res = res.strip()  # Clean any remaining whitespace
                
                # Remove the opening [ since we're appending to existing partial JSON
                if res.startswith('['):
                    res = res[1:]
                
                res = res.strip()  # Clean any whitespace after removing [
                
                # For movimientos: append new movements to the existing array
                completed_response = clean + res
                
                # Clean up any trailing commas that might create invalid JSON
                completed_response = self._fix_trailing_commas(completed_response)
                
                # Check if this completes the movimientos array and we need to add trusts array
                if self._ends_movimientos_array(completed_response):
                    logger.info("Movimientos array completed, adding trusts field")
                    # Add the trusts field with empty array

                    # If it ends with ] only, add comma and trusts field, then close main object
                    if completed_response.rstrip().endswith(']'):
                        completed_response = completed_response.rstrip() + ',\n    "trusts": []\n}\n```'
                    # If it ends with ] }, remove the }, add comma, trusts field, then close
                    elif completed_response.rstrip().endswith('}'):
                        # Remove the final }
                        completed_response = completed_response.rstrip()[:-1]
                        # Remove any trailing whitespace and the ] if present
                        completed_response = completed_response.rstrip()
                        if completed_response.endswith(']'):
                            completed_response += ',\n    "trusts": []\n}\n```'
                        else:
                            completed_response += '\n    "trusts": []\n}\n```'

                return completed_response
            else:
                logger.warning(f"Could not find complete movimientos context - value: {value}, subsequentBalance: {subsequentBalance}")

        elif cut_context == "encargos":
            # Find last complete encargo in trusts
            trustName = self.find_last_complete_encargo(clean,"trustName")
            trustDate = self.find_last_complete_encargo(clean,"trustDate")
            logger.info(f"Found encargos context - trustName: {trustName}, trustDate: {trustDate}")

            # Check if encargos array is empty (just created)
            is_empty_encargos = self._is_empty_encargos_array(clean)
            
            if (trustName and trustDate) or is_empty_encargos:
                if is_empty_encargos:
                    logger.info("Reprocessing encargos from beginning - empty array detected")
                    # Use the prompt without context for starting fresh
                    prompt_with_context = self.read_encargos_prompt_without_context()
                    # Prepare clean to receive new encargos by opening the array
                    # Replace [] with [ to start adding elements
                    clean = clean.replace('"trusts": []', '"trusts": [')
                else:
                    logger.info(f"Reprocessing encargos from: trustName{trustName}, trustDate{trustDate}")
                    prompt_with_context = self.read_encargos_prompt_with_context(trustName, trustDate)

                mres = await self.model_service.make_prompt_with_file(prompt_with_context, self.file.part)
                res = mres.text.strip()
                
                # Remove markdown code block formatting if present
                if res.startswith('```json'):
                    res = res[7:]  # Remove ```json
                elif res.startswith('```'):
                    res = res[3:]   # Remove ```
                
                if res.endswith('```'):
                    res = res[:-3]  # Remove trailing ```
                
                res = res.strip()  # Clean any remaining whitespace
                
                # Remove the opening [ since we're appending to existing partial JSON
                if res.startswith('['):
                    res = res[1:]
                
                res = res.strip()  # Clean any whitespace after removing [
                
                # For encargos: handle both cases - adding encargos or closing empty array
                
                # Check if Gemini returned an empty array (no encargos found)
                if self._is_empty_response(res):
                    logger.info("Gemini returned empty response - no encargos found, closing array")
                    # Close the empty encargos array and complete JSON
                    # Replace the open [ with closed [] and close main object
                    completed_response = clean.replace('"trusts": [', '"trusts": []')
                    if not completed_response.rstrip().endswith('}'):
                        completed_response = completed_response.rstrip() + '\n}'
                    # Add closing markdown code block
                    completed_response += '\n```'
                    return completed_response
                
                # Normal case: append new encargos to the existing array
                completed_response = clean + res
                
                # Clean up any trailing commas that might create invalid JSON
                completed_response = self._fix_trailing_commas(completed_response)
                
                # If the response completes the encargos array, ensure proper JSON closure
                if self._ends_encargos_array(completed_response):
                    # Ensure the main JSON object is properly closed
                    if not completed_response.rstrip().endswith('}'):
                        completed_response = completed_response.rstrip() + '\n}'
                    # Add closing markdown code block
                    completed_response += '\n```'
                
                return completed_response
            else:
                logger.warning(f"Could not find complete encargos context - trustName: {trustName}, trustDate: {trustDate}")
        else:
            logger.warning(f"Unknown cut context: {cut_context}")

        logger.warning("ExtractReprocessService returning None - no valid reprocessing path found")
        return None

    def determine_cut_context(self, s: str) -> str:
        """
        Determines if the JSON was cut during 'movements' or 'trusts'
        """
        # Find the last occurrence of both field names
        movimientos_pos = s.rfind('"movements"')
        trusts_pos = s.rfind('"trusts"')

        # If neither is found, we can't determine context
        if movimientos_pos == -1 and trusts_pos == -1:
            return "unknown"
        
        # The one that appears last in the string is likely where the cut occurred
        if movimientos_pos > trusts_pos:
            return "movimientos"
        else:
            return "trusts"

    def find_last_complete_movement(self, s: str, attribute: str) -> str:
        """
        Finds the last complete movement identifier in movements
        Handles both string and numeric values
        """
        index = s.rfind(f'"{attribute}"')
        if index == -1:
            return None
        
        # Find the colon after the field name
        colon_pos = s.find(':', index)
        if colon_pos == -1:
            return None
        
        # Skip whitespace after colon
        pos = colon_pos + 1
        while pos < len(s) and s[pos].isspace():
            pos += 1
        
        if pos >= len(s):
            return None
        
        # Handle quoted string values
        if s[pos] == '"':
            # Find closing quote
            start_quote = pos + 1
            end_quote = s.find('"', start_quote)
            if end_quote == -1:
                return None
            
            # Extract the field value
            field_value = s[start_quote:end_quote]
            
            # Validate field value
            if len(field_value) > 0:
                return field_value
        
        # Handle numeric values (unquoted)
        else:
            # Find the end of the numeric value
            start_pos = pos
            while pos < len(s) and (s[pos].isdigit() or s[pos] in '.-'):
                pos += 1
            
            # Check if we found a valid numeric value
            if pos > start_pos:
                field_value = s[start_pos:pos]
                # Basic validation for numeric values
                try:
                    float(field_value)
                    return field_value
                except ValueError:
                    return None
        
        return None

    def find_last_complete_encargo(self, s: str, attribute: str) -> str:
        """
        Finds the last complete encargo identifier in trusts
        Handles both string and numeric values
        """
        index = s.rfind(f'"{attribute}"')
        if index == -1:
            return None
        
        # Find the colon after the field name
        colon_pos = s.find(':', index)
        if colon_pos == -1:
            return None
        
        # Skip whitespace after colon
        pos = colon_pos + 1
        while pos < len(s) and s[pos].isspace():
            pos += 1
        
        if pos >= len(s):
            return None
        
        # Handle quoted string values
        if s[pos] == '"':
            # Find closing quote
            start_quote = pos + 1
            end_quote = s.find('"', start_quote)
            if end_quote == -1:
                return None
            
            # Extract the field value
            field_value = s[start_quote:end_quote]
            
            # Validate field value
            if len(field_value) > 0:
                return field_value
        
        # Handle numeric values (unquoted)
        else:
            # Find the end of the numeric value
            start_pos = pos
            while pos < len(s) and (s[pos].isdigit() or s[pos] in '.-'):
                pos += 1
            
            # Check if we found a valid numeric value
            if pos > start_pos:
                field_value = s[start_pos:pos]
                # Basic validation for numeric values
                try:
                    float(field_value)
                    return field_value
                except ValueError:
                    return None
        
        return None

    def read_movimientos_prompt_with_context(self, value: str, subsequentBalance: str) -> str:
        """
        Read the movimientos reprocess prompt and insert context
        """
        try:
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            prompt_path = os.path.join(current_dir, "prompts", "extractos_movimientos_reprocess.txt")
            
            with open(prompt_path, "r", encoding='utf-8') as f:
                prompt_content = f.read()
            
            # Replace placeholder with last item information
            modified_prompt = prompt_content.replace("{value}", value).replace("{subsequentBalance}", subsequentBalance)

            return modified_prompt
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        except Exception as e:
            raise RuntimeError(f"Error reading prompt file: {e}")

    def read_encargos_prompt_with_context(self, trust_name: str, trust_date: str) -> str:
        """
        Read the encargos reprocess prompt and insert context
        """
        try:
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            prompt_path = os.path.join(current_dir, "prompts", "extractos_encargos_reprocess.txt")
            
            with open(prompt_path, "r", encoding='utf-8') as f:
                prompt_content = f.read()
            
            # Replace placeholder with last item information
            modified_prompt = prompt_content.replace("{trustName}", trust_name).replace("{trustDate}", trust_date)
            
            return modified_prompt
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        except Exception as e:
            raise RuntimeError(f"Error reading prompt file: {e}")

    def read_encargos_prompt_without_context(self) -> str:
        """
        Read the encargos reprocess prompt without context for starting fresh
        """
        try:
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            prompt_path = os.path.join(current_dir, "prompts", "extractos_encargos_reprocess.txt")
            
            with open(prompt_path, "r", encoding='utf-8') as f:
                prompt_content = f.read()
            
            # Remove the context-specific instruction and placeholders
            # Replace the context instruction with instruction to start from beginning
            modified_prompt = prompt_content.replace(
                'Solo debes llenar la lista con la informacion desde el encargo con "trustName" {trustName} y "trustDate" {trustDate} sin incluirlo.',
                'Extrae TODOS los encargos que encuentres en el documento desde el principio.'
            )
            
            # Remove any placeholder references that might remain
            modified_prompt = modified_prompt.replace("{trustName}", "").replace("{trustDate}", "")
            
            return modified_prompt
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        except Exception as e:
            raise RuntimeError(f"Error reading prompt file: {e}")

    def read_movimientos_prompt_without_context(self) -> str:
        """
        Read the movimientos reprocess prompt without context for starting fresh
        """
        try:
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            prompt_path = os.path.join(current_dir, "prompts", "extractos_movimientos_reprocess.txt")
            
            with open(prompt_path, "r", encoding='utf-8') as f:
                prompt_content = f.read()
            
            # Remove the context-specific instruction and placeholders
            # Replace the context instruction with instruction to start from beginning
            modified_prompt = prompt_content.replace(
                'Solo debes llenar la lista con la informacion desde el movimiento con "value" {value} y "subsequentBalance" {subsequentBalance} sin incluirlo',
                'Extrae TODOS los movimientos bancarios que encuentres en el documento desde el principio.'
            )
            
            # Remove any placeholder references that might remain
            modified_prompt = modified_prompt.replace("{value}", "").replace("{subsequentBalance}", "")
            
            return modified_prompt
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        except Exception as e:
            raise RuntimeError(f"Error reading prompt file: {e}")


    

    
    def _ends_movimientos_array(self, response: str) -> bool:
        """
        Check if the response properly ends the movements array
        and is ready for the trusts array to be added
        """
        stripped = response.rstrip()

        # Check if we have movements but not trusts
        has_movimientos = '"movements"' in response
        has_trusts = '"trusts"' in response

        # If we have movimientos but no trusts
        if has_movimientos and not has_trusts:
            # Check if it ends with ] (closing the movements array)
            # This could be followed by }, whitespace, or end of string
            if re.search(r']\s*$', stripped):
                return True
            # Also check if it ends with ] followed by whitespace and }
            if re.search(r']\s*}$', stripped):
                return True
        
        return False

    def _ends_trusts_array(self, response: str) -> bool:
        """
        Check if the response properly ends the trusts array
        """
        # Look for the end of trusts array
        stripped = response.rstrip()

        # Check if we have trusts
        has_trusts = '"trusts"' in response

        if has_trusts:
            # Check if it ends with ] (end of trusts array) but not yet the main object closure
            import re
            # Look for pattern: ] at the end, which should be the end of trusts array
            if re.search(r']\s*$', stripped):
                return True
        
        return False

    def _is_empty_trusts_array(self, response: str) -> bool:
        """
        Check if the trusts array is empty []
        """
        # Look for the pattern "trusts": []
        import re
        pattern = r'"trusts"\s*:\s*\[\s*\]'
        return bool(re.search(pattern, response))

    def _is_empty_movimientos_array(self, response: str) -> bool:
        """
        Check if the movements array is empty or just opened [
        """
        # Look for the pattern "movements": [ with no complete objects
        import re
        # Pattern matches "movements": [ followed by whitespace and potentially incomplete content
        pattern = r'"movements"\s*:\s*\[\s*$'
        return bool(re.search(pattern, response.rstrip()))

    def _fix_trailing_commas(self, json_str: str) -> str:
        """
        Fix trailing commas that might create invalid JSON
        """
        # Remove trailing commas before ] or }
        # Pattern: comma followed by optional whitespace, then ] or }
        fixed = re.sub(r',\s*([}\]])', r'\1', json_str)
        return fixed

    def _is_empty_response(self, response: str) -> bool:
        """
        Check if Gemini returned an empty response indicating no encargos found
        """
        stripped = response.strip()
        
        # Check for common empty response patterns
        empty_patterns = [
            r'^\[\s*\]$',  # Empty array []
            r'^\s*$',       # Just whitespace
            '[]',           # Literal empty array
        ]
        
        for pattern in empty_patterns:
            if re.match(pattern, stripped):
                return True
        
        # Check for text responses indicating no encargos
        no_encargos_indicators = [
            'no hay encargos',
            'no se encontraron encargos',
            'no encargos',
            'sin encargos',
            'no more encargos',
            'empty',
            'ningún encargo',
            'no existen encargos'
        ]
        
        stripped_lower = stripped.lower()
        for indicator in no_encargos_indicators:
            if indicator in stripped_lower:
                return True
        
        return False

    @staticmethod
    def clean_str(s: str) -> str:
        """
        Devuelve la MISMA cadena de entrada pero cortada justo después del último
        elemento COMPLETO de la ÚLTIMA lista del objeto raíz, dejando una coma.
        - Supone JSON con comillas dobles.
        - Ignora brackets/llaves dentro de cadenas (maneja escapes).
        - No añade coma si lo siguiente es ']' o '}'.
        """
        t = s.rstrip()
        n = len(t)

        # --- mask of positions inside strings ("...") ---
        m = [False] * n
        in_str = esc = False
        for i, ch in enumerate(t):
            if in_str:
                m[i] = True
                if esc: esc = False
                elif ch == '\\': esc = True
                elif ch == '"': in_str = False
            else:
                if ch == '"':
                    in_str = True
                    m[i] = True

        # --- locate the opening of the LAST array at level 0 ---
        depth = 0
        arr_start = -1
        for i, ch in enumerate(t):
            if m[i]: 
                continue
            if ch == '[':
                if depth == 0:
                    arr_start = i
                depth += 1
            elif ch == ']':
                if depth > 0:
                    depth -= 1
        if arr_start == -1:
            return t  # no array found

        # --- traverse right-to-left within that array ---
        i = n - 1
        arr_rel = braces = 0
        last_end = None  # index of the '}' closing the last complete object
        while i > arr_start:
            if m[i]:
                i -= 1; continue
            ch = t[i]
            if ch == ']':
                arr_rel += 1
            elif ch == '[':
                if arr_rel > 0: arr_rel -= 1
            elif ch == '}':
                braces += 1
                if braces == 1 and arr_rel == 0 and last_end is None:
                    last_end = i
            elif ch == '{':
                if braces > 0:
                    braces -= 1
                    if braces == 0 and arr_rel == 0 and last_end is not None:
                        end = last_end  # end of the last complete element
                        # Is there already a comma or closing brace after?
                        j = end + 1
                        while j < n and t[j].isspace(): j += 1
                        if j < n and t[j] == ',':
                            return t[:j + 1]
                        if j < n and t[j] in ']}':
                            return t[:end + 1]
                        return t[:end + 1] + ','
            i -= 1

        # No complete element found: return up to '[' preserving trailing spaces
        k = arr_start + 1
        while k < n and t[k].isspace(): k += 1
        return t[:k]