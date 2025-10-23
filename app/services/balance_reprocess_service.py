from app.services.model_service import get_model_service, ModelService
from app.utils.file import PartFile

class BalanceReprocessService:

    def __init__(self, model_service: ModelService, file: PartFile):
        self.model_service = model_service
        self.file = file

    async def reprocess(self, gemini_response: str):
        # Logic to reprocess the balance
        clean = BalanceReprocessService.clean_str(gemini_response)
        last_order = self.find_last_complete_order(clean)
        if last_order:
            # Read the fiduciary balance prompt and insert the last_order parameter
            prompt_with_order = self.read_prompt_with_last_order(last_order)
            mres = await self.model_service.make_prompt_with_file(prompt_with_order, self.file.part)
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
            # Fix the string manipulation logic
            if len(res) > 0 and res[-1] == ']':
                res += '}```'
                return clean + res
            return clean + res

        return None

    def read_prompt_with_last_order(self, last_order: str) -> str:
        """
        Read the fiduciary_balance_prompt.txt file and insert the last_order parameter
        """
        try:
            import os
            # Use absolute path to avoid working directory issues
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            prompt_path = os.path.join(current_dir, "prompts", "ficuciary_balance_reprocess.txt")
            
            with open(prompt_path, "r", encoding='utf-8') as f:
                prompt_content = f.read()
            
            
            # Insert the additional instruction before the final closing quotes
            modified_prompt = prompt_content.replace("{last_order}", last_order)

            return modified_prompt
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        except Exception as e:
            raise RuntimeError(f"Error reading prompt file: {e}")
    
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

        # --- máscara de posiciones dentro de strings ("...") ---
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

        # --- localizar la apertura de la ÚLTIMA lista a nivel 0 ---
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
            return t  # no hay lista

        # --- recorrer de derecha a izquierda dentro de esa lista ---
        i = n - 1
        arr_rel = braces = 0
        last_end = None  # índice del '}' que cierra el último objeto completo
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
                        end = last_end  # fin del último elemento completo
                        # ¿ya hay coma o cierre después?
                        j = end + 1
                        while j < n and t[j].isspace(): j += 1
                        if j < n and t[j] == ',':
                            return t[:j + 1]
                        if j < n and t[j] in ']}':
                            return t[:end + 1]
                        return t[:end + 1] + ','
            i -= 1

        # No hay elemento completo: devolver hasta '[' preservando espacios posteriores
        k = arr_start + 1
        while k < n and t[k].isspace(): k += 1
        return t[:k]
    
    def find_last_complete_order(self, s: str) -> str:
        """
        Finds the last complete account number in the string.
        Handles cases like: "accountNumber": "6000201004564"
        """
        index = s.rfind('"accountNumber"')
        if index == -1:
            return None
        
        # Find the colon after "accountNumber"
        colon_pos = s.find(':', index)
        if colon_pos == -1:
            return None
        
        # Skip whitespace after colon
        pos = colon_pos + 1
        while pos < len(s) and s[pos].isspace():
            pos += 1
        
        if pos >= len(s):
            return None
        
        # Expect opening quote
        if s[pos] != '"':
            return None
        
        # Find closing quote
        start_quote = pos + 1
        end_quote = s.find('"', start_quote)
        if end_quote == -1:
            return None
        
        # Extract the account number
        account_number = s[start_quote:end_quote]
        
        # Validate it's a valid account number (digits only)
        if account_number.isdigit() and len(account_number) > 0:
            return account_number
        
        return None
    