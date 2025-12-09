import logging
import asyncio
import httpx
import uuid
import secrets
from app.core.client import SuperliveClient
from app.core.config import config

logger = logging.getLogger("superlive.modules.api.viewmodel")

class SuperliveError(Exception):
    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)

class ApiViewModel:
    
    async def _make_request(self, method: str, endpoint: str, client, error_context: str = "Request failed", base_url: str = None, **kwargs):
        """
        Helper method to make requests with fallback to backup URL on network errors or specific status codes.
        If base_url is specified, strict usage of that base URL is enforced (no failover to others).
        """
        if base_url:
            # If explicit base URL is provided, remove trailing slash if endpoint has leading slash to avoid double slash
            # But the user provided URLs have variations. Let's be careful.
            # config.py has no trailing flash for 1 & 2, but has it for 3. 
            # endpoint usually starts with /. 
            # httpx handles this usually, but let's be safe:
            if base_url.endswith("/") and endpoint.startswith("/"):
                url = f"{base_url[:-1]}{endpoint}"
            elif not base_url.endswith("/") and not endpoint.startswith("/"):
                url = f"{base_url}/{endpoint}"
            else:
                url = f"{base_url}{endpoint}"
            
            urls = [url]
        else:
            urls = [
                f"{config.API_BASE_URL}{endpoint}",
                f"{config.API_BASE_URL_BACKUP}{endpoint}"
            ]
        
        last_exception = None
        
        for i, url in enumerate(urls):
            is_backup = i > 0
            try:
                if is_backup:
                    logger.warning(f"Retrying with backup URL: {url}")
                    
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                # If it's a 5xx or 403, we might want to try backup
                # Also adding 404 just in case the primary API routing is broken
                # The user mentioned "code 12", but we catch standard HTTP connection issues
                if e.response.status_code in [403, 502, 503, 504] and not is_backup:
                    logger.warning(f"Primary URL failed with status {e.response.status_code}. Attempting backup.")
                    last_exception = e
                    continue
                
                logger.error(f"{error_context}: {e.response.text}")
                try:
                    details = e.response.json()
                except:
                    details = {"error": e.response.text}
                raise SuperliveError(error_context, e.response.status_code, details)
                
            except (httpx.NetworkError, httpx.TimeoutException) as e:
                if not is_backup:
                    logger.warning(f"Network error on primary URL: {e}. Attempting backup.")
                    last_exception = e
                    continue
                
                logger.error(f"Unexpected {error_context.lower()} error: {e}")
                # If we have a last_exception from primary, maybe we should mention that too?
                # But usually the last error (backup failed) is the one to raise
                raise SuperliveError(f"Unexpected error: {str(e)}")
                
            except Exception as e:
                logger.error(f"Unexpected {error_context.lower()} error: {e}")
                raise SuperliveError(f"Unexpected error: {str(e)}")
                
        # Should not reach here if loop works correctly
        raise SuperliveError(f"Unexpected error: {str(last_exception)}")

    async def login(self, email, password, client=None, base_url=None):
        if client is None:
            client = SuperliveClient.get_client()
        
        payload = {
            "client_params": self._get_client_params(),
            "email": email,
            "password": password
        }
        
        # Fixed: Removed undefined 'headers' variable usage
        return await self._make_request(
            "POST", 
            "/signup/email_signin", 
            client, 
            json=payload, 
            error_context="Login failed",
            base_url=base_url
        )

    async def get_profile(self, token, client=None, base_url=None):
        if client is None:
            client = SuperliveClient.get_client()
        
        headers = client.headers.copy()
        headers["authorization"] = f"Token {token}"
        
        payload = {
            "client_params": self._get_client_params()
        }
        
        return await self._make_request(
            "POST", 
            "/own_profile", 
            client, 
            headers=headers, 
            json=payload, 
            error_context="Get profile failed",
            base_url=base_url
        )

    async def send_gift(self, token, gift_details, client=None, base_url=None):
        if client is None:
            client = SuperliveClient.get_client()
        
        headers = client.headers.copy()
        headers["authorization"] = f"Token {token}"
        
        livestream_id = gift_details.get('livestream_id')
        
        # Generate guid if not provided
        guids = gift_details.get("guids", [])
        if not guids:
            guids = [str(uuid.uuid4())]
        
        payload = {
            "client_params": self._get_client_params(livestream_id),
            "gift_context": gift_details.get("gift_context", 1),
            "livestream_id": livestream_id,
            "gift_id": gift_details.get("gift_id"),
            "guids": guids
        }
        
        return await self._make_request(
            "POST", 
            "/livestream/chat/send_gift", 
            client, 
            headers=headers, 
            json=payload, 
            error_context="Send gift failed",
            base_url=base_url
        )

    async def get_livestream(self, token, livestream_id, client=None, base_url=None):
        if client is None:
            client = SuperliveClient.get_client()
        
        headers = client.headers.copy()
        headers["authorization"] = f"Token {token}"
        
        payload = {
            "client_params": self._get_client_params(livestream_id),
            "livestream_id": livestream_id
        }
        
        return await self._make_request(
            "POST", 
            "/livestream/retrieve", 
            client, 
            headers=headers, 
            json=payload, 
            error_context="Get livestream failed",
            base_url=base_url
        )

    async def send_verification_code(self, email, client=None, base_url=None):
        if client is None:
            client = SuperliveClient.get_client()
        
        payload = {
            "client_params": self._get_client_params(),
            "email": email,
            "force_new": False
        }
        
        return await self._make_request(
            "POST", 
            "/signup/send_email_verification_code", 
            client, 
            json=payload, 
            error_context="Send verification code failed",
            base_url=base_url
        )

    async def verify_email(self, email_verification_id, code, client=None, base_url=None):
        if client is None:
            client = SuperliveClient.get_client()
        
        payload = {
            "client_params": self._get_client_params(),
            "email_verification_id": email_verification_id,
            "code": int(code)
        }
        
        return await self._make_request(
            "POST", 
            "/signup/verify_email", 
            client, 
            json=payload, 
            error_context="Verify email failed",
            base_url=base_url
        )

    async def complete_signup(self, email, password, client=None, base_url=None):
        if client is None:
            client = SuperliveClient.get_client()
        
        payload = {
            "client_params": self._get_client_params(),
            "email": email,
            "password": password
        }
        
        return await self._make_request(
            "POST", 
            "/signup/email", 
            client, 
            json=payload, 
            error_context="Complete signup failed",
            base_url=base_url
        )

    async def logout(self, token, client=None, base_url=None):
        if client is None:
            client = SuperliveClient.get_client()
        
        headers = client.headers.copy()
        headers["authorization"] = f"Token {token}"
        
        payload = {
            "client_params": self._get_client_params()
        }
        
        return await self._make_request(
            "POST", 
            "/user/logout", 
            client, 
            headers=headers, 
            json=payload, 
            error_context="Logout failed",
            base_url=base_url
        )

    async def update_profile(self, token, client=None, base_url=None):
        if client is None:
            client = SuperliveClient.get_client()
            
        headers = client.headers.copy()
        headers["authorization"] = f"Token {token}"
        
        # Random Name Logic
        import random
        names = [
            "Jacqueline Levy", "Harold Love", "Avianna Sloan", "Ocean Moran", "Celeste Heath", "Lionel Silva", "Lucia McGee", "Conner Hendrix", "Zhuri Joseph", "Kyle Stephens", 
            "Millie Compton", "Abner Dodson", "Etta Fuller", "Andre McCormick", "Macie Farley", "Graysen Colon", "Remy Gregory", "Travis Waters", "Bristol Boone", "Mauricio Valenzuela", 
            "Henley O’Neill", "Marcel Crawford", "Aubree Dennis", "Emanuel Curry", "Alison Whitney", "Jeffery Garrison", "Cadence Booth", "Chaim Curtis", "Alexis Rios", "Israel Arellano", 
            "Faye Snyder", "Thiago Salinas", "Royalty Hester", "Rene Nunez", "Mya Ramirez", "David Christian", "Anahi Tanner", "Bruno Stokes", "Miranda Bailey", "Axel Lim", 
            "Giavanna Paul", "Noel Preston", "Indie Reyes", "Eli Moody", "Elaine Cobb", "Raphael Manning", "Jennifer Chase", "Otis Johnston", "Laila Durham", "Kellen Graham", 
            "Alaia Carter", "Maverick Rivas", "Averie Avila", "Jaylen Vincent", "Allyson Phillips", "Andrew Reeves", "Lana Cain", "Benson Dominguez", "Raegan Sellers", "Madden Macdonald", 
            "Rosalia Nielsen", "Tru Cortez", "Haven McKenzie", "Scott Herring", "Denver Petersen", "Samson Hahn", "Fallon Avalos", "Coen Strong", "Margo Case", "Bentlee Frost", 
            "Paula Levy", "Harold Villanueva", "Monroe Mendez", "Arthur Sandoval", "Elsie Donovan", "Brayan Mueller", "Imani Wallace", "Chase Sheppard", "Veda Galvan", "Kingsley King", 
            "Victoria Washington", "Juan McLean", "Sky Singleton", "Landyn Snyder", "Callie Beard", "Nathanael Rubio", "Hadassah Dorsey", "Enoch Cummings", "Nylah Delacruz", "Memphis Avila", 
            "Amiyah Cruz", "Ryan Dunn", "Olive Walter", "Lochlan Norman", "Malani McBride", "Denver Barnett", "Harlow Bridges", "Mohammed Moreno", "Mary Valenzuela", "Jamari Krueger", 
            "Kamari Ellison", "Kye Vance", "Maxine Noble", "Idris Young", "Zoey Pham", "Russell Lopez", "Gianna Arias", "Alec Mathews", "Sloan Spears", "Ameer Navarro", 
            "Winter Stark", "Kristopher Wagner", "Maeve Rubio", "Titan Flowers", "Ariya Fry", "Jacoby Morales", "Skylar McGuire", "Casey Hensley", "Malaya Lucas", "Chance Thornton", 
            "Haisley Mendez", "Arthur Lynch", "Malia Sharp", "Royce Rose", "Magnolia Cabrera", "Cade Ryan", "Morgan Nelson", "Dylan Underwood", "Ensley Leach", "Westin Hubbard", 
            "Rosie Novak", "Bishop Strong", "Margo Nielsen", "Tru Franco", "Charleigh Ruiz", "Austin Floyd", "Yaretzi Fisher", "Gael McLean", "Sky Conway", "Orlando Delarosa", 
            "Iyla Mata", "Ray Burnett", "Emberly Pratt", "Rowen Osborne", "Shelby Hodges", "Alonzo Turner", "Brooklyn Pennington", "Bobby Logan", "Kora Bowen", "Trevor Flowers", 
            "Ariya Pace", "Dior Higgins", "Leighton Williamson", "Emerson Adkins", "Emelia Foster", "Kayden Nunez", "Mya Bass", "Landen Frazier", "Octavia Powers", "Sean Espinoza", 
            "Lucille Richardson", "Robert Bravo", "Amoura Rowland", "Eliezer Roach", "Lyanna Campbell", "Christopher Golden", "Giuliana Rangel", "Saint Baldwin", "Esmeralda Vo", "Gordon Moreno", 
            "Mary Hall", "Thomas Larson", "Alayna Bridges", "Mohammed White", "Layla Henry", "Carlos Phillips", "Naomi Pitts", "Trey Clayton", "Saige Holloway", "Sutton Proctor", 
            "Chandler Edwards", "Adrian Garrison", "Cadence Moss", "Porter Pennington", "Yareli Roman", "Kian Munoz", "Kehlani Terrell", "Jaxen Fernandez", "Amara Wade", "Jake Leach", 
            "Martha Hall", "Thomas Church", "Ayleen Hull", "Salem Carpenter", "Lilly Salas", "Zaiden Stephens", "Millie Goodwin", "Kaison Cameron", "Julie Huang", "Ayaan Choi", 
            "Karla Ashley", "Kylen Delarosa", "Iyla Strickland", "Keegan Kelly", "Ruby Shannon", "Eliel Parker", "Aubrey Farmer", "Jamison Lopez", "Gianna Vincent", "Aarav Ford", 
            "Alexandra Burnett", "Davis Logan", "Kora Fischer", "Leonidas Good", "Nathalia Mercado", "Abram Melendez", "Bethany Murphy", "Cameron Person", "Dylan Rowland", "Eliezer Romero", 
            "Eliza Navarro", "Reid Beck", "Gia Rosas", "Remi Salgado", "Avalynn Austin", "Omar Allison", "Chelsea Aguilar", "Milo Cano", "Egypt Costa", "Kenji Hood", 
            "Briana Arnold", "Abraham Murillo", "Mikaela Estrada", "Phoenix Carpenter", "Lilly Reid", "Josue Anderson", "Ella Collier", "Edison Cook", "Aaliyah Hall", "Thomas Barnes", 
            "Liliana Porter", "Rhett Shepherd", "Katalina Kemp", "Melvin Curry", "Alison Gomez", "Isaiah Little", "Harley Estrada", "Phoenix Mueller", "Imani White", "Aiden Glass", 
            "Clare Compton", "Abner Wallace", "Arianna Fleming", "Fernando Richmond", "Whitney Rivera", "Charles Villegas", "Jessie Pearson", "Gunner Walker", "Hazel Curry", "Briggs Cervantes", 
            "Aylin Alexander", "Kingston Fisher", "Arya Hayes", "Legend Lambert", "Nina Morales", "Aaron Maxwell", "Kyla Houston", "Sylas McPherson", "Emmaline Sanford", "Truett Scott", 
            "Aurora Parra", "Davion Marshall", "Adalyn Espinoza", "Dallas Solomon", "Mylah Shah", "Zain Craig", "Brynn Cabrera", "Cade Bishop", "Brooklynn Crane", "Fox Fields", 
            "Annie McDonald", "Calvin Herring", "Denver Perkins", "Kyrie Pierce", "Arabella Kim", "Roman Collins", "Kinsley Rodgers", "Mathias Newman", "Oaklynn Avalos", "Coen Cano", 
            "Egypt Case", "Bentlee Peralta", "Malayah Flynn", "Kannon Walton", "Scarlet Pittman", "Valentino Robinson", "Nora Parra", "Davion Huerta", "Dulce Rodriguez", "Henry Shaw", 
            "Emersyn Stanton", "Zyair Berger", "Laylah Lowery", "Jaxxon Leal", "Murphy Duran", "Ismael Kramer", "Hanna Graham", "Giovanni Carrillo", "Kaylani Knox", "Valentin Spears", 
            "Isabela Rivers", "Bear Rhodes", "Tatum Lewis", "Wyatt Lawson", "Phoebe Duran", "Ismael Dickerson", "Opal Frost", "Dario Larson", "Alayna Gould", "Blaine Hinton", 
            "Jaelynn Montgomery", "Maximiliano Yang", "Angelina Walls", "Larry Rios", "Brooke Cunningham", "Alejandro Cunningham", "Marley Griffith", "Franklin Barr", "Noemi Allison", "Dennis Nicholson", 
            "Justice Wilkerson", "Carmelo Kelley", "Rosalie Santana", "Mohamed Donovan", "Azariah Jenkins", "Declan Bauer", "Haley Moss", "Porter Little", "Harley Zamora", "Quentin Todd", 
            "Zariah Rocha", "Onyx Aguilar", "Josie Schultz", "Cody Burgess", "Emory Welch", "Hendrix Wyatt", "Liberty Alexander", "Kingston Woodward", "Drew Dunlap", "Aries Person", 
            "Dylan Thomas", "Logan Houston", "Lylah Clark", "John Contreras", "Daniela Fitzgerald", "Peyton Sanchez", "Aria Barajas", "Brennan Haley", "Addilynn Delacruz", "Memphis Lin", 
            "Makenna Gray", "Nicholas Bass", "Zahra Trujillo", "Apollo Christian", "Anahi Buck", "Jon Warren", "Sloane Wilkinson", "Leonard Hendrix", "Zhuri Keith", "Jagger Horne", 
            "Marlowe Barton", "Cassius Travis", "Mazikee Frazier", "Callum Taylor", "Sofia Pollard", "Jad Vu", "Kimora Molina", "Prince Levy", "Flora Holt", "Niko Orr", 
            "Alaiya Mayer", "Yahir Daniel", "Joy Olsen", "Skyler Burgess", "Emory Foley", "Mohammad Mosley", "Zaniyah Bravo", "Genesis Frank", "Dior Lopez", "Michael Blevins", 
            "Aila White", "Aiden Steele", "Rylie Douglas", "Derek Lam", "Karina Stark", "Kristopher Ryan", "Morgan Sawyer", "Jefferson Houston", "Lylah Randolph", "Eugene Woodard", 
            "Aubrie Hurley", "Van Davila", "Rayne Patrick", "Derrick Cole", "Margaret Romero", "Bryson West", "Remi Estes", "Hakeem Robertson", "Harmony Rosario", "Jedidiah Harrell", 
            "Kara Dejesus", "Rio Garrison", "Cadence Parra", "Davion Rocha", "Emmie Ball", "Shane Henderson", "Maria Williams", "Oliver Bishop", "Brooklynn Duffy", "Kyng Raymond", 
            "Hadlee Williamson", "Emerson Drake", "Jayleen Calderon", "Oakley Reeves", "Lana Poole", "Quincy Cano", "Egypt Swanson", "Hugo Maddox", "Zainab Cortes", "Banks Townsend", 
            "Azalea Ho", "Morgan Rollins", "Araceli Atkins", "Cason Stewart", "Maya Duke", "Kalel Frank", "Dior Ortiz", "Landon House", "Sariah Steele", "Elian Crawford", 
            "Aubree Decker", "Taylor Moore", "Emily Kemp", "Melvin Sierra", "Marceline Holt", "Niko Rivas", "Averie Edwards", "Adrian Bell", "Melody Jacobson", "Legacy Anthony", 
            "Macy Walsh", "Bodhi Leon", "Amora Kerr", "Louie Henson", "Kinslee David", "Alonso Hodges", "Eve Stevenson", "Callan Pratt", "Ailani Nixon", "Cory Golden", 
            "Giuliana Ward", "Jameson Shaw", "Emersyn Buchanan", "Enrique Burch", "Freyja Vaughn", "Remy Duncan", "Elise Silva", "Luka Bowman", "Fiona Baker", "Ezra Moran", 
            "Celeste Reid", "Josue Swanson", "Helen Knapp", "Boden Frazier", "Octavia Hinton", "Frankie Ryan", "Morgan Michael", "Bronson Norris", "Arielle Hull", "Salem Palmer", 
            "Juniper Ali", "Arjun Barrera", "Beatrice Ventura", "Branson Costa", "Robin Li", "Jorge Morgan", "Delilah Avery", "Jakari Hall", "Leah Dougherty", "Brett Larson", 
            "Alayna Lester", "Lee Hayes", "Iris Moon", "Nova Morales", "Skylar Tyler", "Emmitt Schwartz", "Lilliana Shah", "Zain Gardner", "Jordyn McCall", "Kiaan Nelson", 
            "Everly Jensen", "Cash Lim", "Giavanna Hughes", "Everett Joseph", "Gracelynn Guzman", "Jude Lin", "Makenna Davenport", "Dariel Herman", "Paulina Ochoa", "Winston Thornton", 
            "Haisley Cameron", "Rayan Bender", "Lilyana Le", "Damien McGee", "Kayleigh Duran", "Ismael Harris", "Penelope Cross", "Fabian Powell", "Vivian Stanley", "Manuel Lang", 
            "Amirah Phelps", "Hamza Huber", "Raquel Farmer", "Jamison Decker", "Aleena Hensley", "Layne Arias", "Aleah Choi", "Khari Parsons", "Maia Cannon", "Archie McIntosh", 
            "Gwen Harrell", "Nelson Yoder", "Emerie Brewer", "Cruz Norman", "Malani Gill", "Matthias Vu", "Kimora Hudson", "Peter Little", "Harley Ramirez", "David Dawson", 
            "Veronica Bravo", "Genesis Vega", "Dakota Faulkner", "Jabari Hubbard", "Rosie Calderon", "Oakley Benjamin", "Jianna Buchanan", "Enrique Rivers", "Kiana Merritt", "Colten Arroyo", 
            "Kyra Gilmore", "Vihaan Hanson", "Mariana Bryan", "Jaxtyn Lowe", "Amari Gallagher", "Marcos Mercado", "Mckinley Morrison", "Maximus Roy", "Savanna Bass", "Landen Salas", 
            "Amber Cobb", "Raphael Jefferson", "Julieta Crosby", "Tristen Tate", "Skye Sampson", "Cain Pierce", "Arabella Stein", "Creed Wallace", "Arianna Schwartz", "Edwin Dougherty", 
            "Alisson Harris", "Samuel Ramos", "Alice Lowe", "Julius McCall", "Kai Kemp", "Melvin Ochoa", "Luciana McCarty", "Blaise Knox", "Kallie Avalos", "Coen Cardenas", 
            "Raven Middleton", "Misael Buchanan", "Maryam Sanchez", "Joseph Rubio", "Hadassah Boyer", "Zeke Vaughan", "Nancy Owen", "Cannon Harrington", "Legacy Fry", "Jacoby Berry", 
            "Annabelle Hart", "Joel Mason", "Sienna Cabrera", "Cade Dorsey", "Addyson Pope", "Gunnar Avalos", "Paloma Hodge", "Reign McDonald", "Daisy Guerrero", "Bryce Reynolds", 
            "Isabelle Campos", "Gideon Dillon", "Laurel Snow", "Houston Buckley", "Theodora Howell", "Bradley Perry", "Clara Watts", "Dakota Carr", "Rowan Powell", "Bennett Steele", 
            "Rylie Mayer", "Yahir Glover", "Alessia Gallegos", "Jonas Madden", "Violette Robles", "Otto Wolfe", "Hallie Morse", "Bode Roberson", "Sasha Abbott", "Kohen Duran", 
            "Willa Alvarez", "Xavier Ferguson", "Juliana McCormick", "Jasiah Mendez", "Londyn Farrell", "Ty Garcia", "Amelia Dejesus", "Rio Horton", "Aitana O’Neill", "Marcel Rich", 
            "Sunny Greene", "Griffin Perkins", "Sage Garner", "Sage Carpenter", "Lilly Yu", "Bryant Pollard", "Marisol Ray", "Arlo Swanson", "Helen McCarty", "Blaise Conway", 
            "Ryann Oliver", "Karson Meyer", "Sara Blackburn", "Zahir Parra", "Dalary Freeman", "Jayce Whitney", "Madalynn Fowler", "Kameron Burns", "Emerson Farmer", "Jamison Cardenas", 
            "Raven Richardson", "Robert Jones", "Sophia Benjamin", "Kyro Chambers", "Makayla Grant", "Leon Daniels", "Ember Fowler", "Kameron Santiago", "Nyla Preston", "Vincenzo Patterson", 
            "Kaylee Rowe", "Kamden Browning", "Princess Zhang", "Isaias McPherson", "Emmaline Berry", "Adonis Kane", "Ellianna Estes", "Hakeem Harris", "Penelope Simmons", "Harrison Huerta", 
            "Dulce McKay", "Joey Yang", "Angelina Rangel", "Saint Burns", "Emerson Felix", "Rodney Crawford", "Aubree McDowell", "Lachlan Lester", "Averi Walsh", "Bodhi Mathis", 
            "Anne Wu", "Kyson Rich", "Sunny Lucero", "Felipe Matthews", "Lila Hoover", "Jaziel Shah", "Angelica Roach", "Caspian Graves", "Elle Kelly", "Cooper Howell", 
            "Mckenna Henderson", "Beau Black", "Molly Cohen", "Killian Wise", "Mira Myers", "Adam Carpenter", "Lilly Townsend", "Alexis Galindo", "Corinne Harmon", "Roberto Vincent", 
            "Allyson Farley", "Graysen Dorsey", "Addyson Andersen", "Alistair Dawson", "Veronica Faulkner", "Jabari Avery", "Meghan Chambers", "Orion Lester", "Averi Haynes", "Kason Hensley", 
            "Malaya Daniels", "Xander Ahmed", "Jolie Robles", "Otto Durham", "Tiffany Rosario", "Jedidiah Pena", "Rachel Stanley", "Manuel Alfaro", "Yasmin Hull", "Salem Rosales", 
            "Kinley Boyd", "Dean Brown", "Charlotte Reilly", "Alvaro Berger", "Laylah Weber", "Crew Rangel", "Gloria Portillo", "Wallace Arroyo", "Kyra Kemp", "Melvin Aguilar", 
            "Josie Cochran", "Danny McGee", "Kayleigh Bond", "Roger Cantu", "Galilea Proctor", "Vance Guevara", "Teresa Blair", "Troy Wade", "Evie Villanueva", "Huxley Hogan", 
            "Kathryn Madden", "Everest Khan", "Mabel Sampson", "Cain Roman", "Astrid Burton", "Zander Ho", "Calliope Brooks", "Jordan Morris", "Genesis Herrera", "River Austin", 
            "Alivia Warren", "Abel Lara", "Heidi Walton", "Dominick Shields", "Analia Stevens", "Zachary McIntyre", "Rebekah Burns", "August Lowe", "Amari Lamb", "Kaysen Clements", 
            "Cara Brock", "Julio Rosas", "Joelle Xiong", "Azrael Roy", "Savanna McCarty", "Blaise McDonald", "Daisy Bradford", "Ander Moyer", "Zola McDowell", "Lachlan Guerrero", 
            "Margot Tyler", "Emmitt Orr", "Alaiya Farmer", "Jamison Adams", "Stella Friedman", "Darwin Drake", "Jayleen Edwards", "Adrian Payne", "London Webb", "Lorenzo McKenzie", 
            "Briar Bryant", "Jonah Mullins", "Maliyah Willis", "Remington Crawford", "Aubree Rivas", "Damon Glover", "Alessia Arias", "Alec Jackson", "Avery Fields", "Clayton Vargas", 
            "Andrea Buckley", "Aryan Flynn", "Dorothy Nava", "Stefan McGuire", "April Winters", "Deandre Boyer", "Chaya Reid", "Josue Carpenter", "Lilly Gates", "Ermias Gallegos", 
            "Ari Padilla", "Jaden Dougherty", "Alisson Hampton", "Hank Macias", "Adley Richards", "Holden Shah", "Angelica Dalton", "Fletcher Barnett", "Harlow Sellers", "Madden Person", 
            "Dylan Christian", "Ledger Franco", "Charleigh Allen", "Carter Booker", "Nataly Cisneros", "Alden Contreras", "Daniela Cherry", "Rome Cook", "Aaliyah Dalton", "Fletcher Greer", 
            "Reina Jaramillo", "Riggs Randolph", "Kailey Farley", "Graysen Rivers", "Kiana Huff", "Finnley Caldwell", "Evelynn Castillo", "Kai Cordova", "Florence Watson", "Greyson Aguilar", 
            "Josie Benitez", "Justice Romero", "Eliza Harris", "Samuel Byrd", "Giselle Martin", "Mateo Abbott", "Melany Owen", "Cannon Waters", "Bristol Hansen", "Charlie Kane", 
            "Ellianna Charles", "Conrad Francis", "Daniella White", "Aiden Jefferson", "Julieta Donaldson", "Canaan Mueller", "Imani Walker", "Luke Davenport", "Adrianna Keith", "Jagger Reyes", 
            "Audrey Hanson", "Khalil Pitts", "Nala Shepard", "Damari Anthony", "Macy Conley", "Marvin Espinosa", "Braylee Strickland", "Keegan Barr", "Noemi Dorsey", "Enoch Alvarado", 
            "Blake Mathews", "Jamir Lawrence", "Lauren Mueller", "Albert Donaldson", "Natasha Smith", "Liam Norris", "Arielle Larsen", "Brycen Stanley", "Gracelyn Larsen", "Brycen Stafford", 
            "Bridget Trevino", "Jaime Salgado", "Avalynn Kelly", "Cooper Santana", "Myra Lawson", "Lane Meza", "Rosa Brown", "Elijah Johnston", "Laila Ochoa", "Winston Bonilla", 
            "Romina Crosby", "Tristen Knapp", "Linda Roy", "Marcelo Yoder", "Emerie Leach", "Westin Guerrero", "Margot Stark", "Kristopher Bullock", "Winnie Solomon", "Musa Cisneros", 
            "Janelle Lyons", "Cyrus Dickson", "Emmalynn Thomas", "Logan Cooper", "Serenity Pollard", "Jad Pope", "Aurelia Robinson", "Matthew Ellis", "Ayla Prince", "Aron Carlson", 
            "Kali Sexton", "Mylo Schmidt", "Kimberly Sampson", "Cain Reeves", "Lana Sweeney", "Nixon Rush", "Maleah Lee", "Jack Lawrence", "Lauren McMillan", "Rocky Pearson", 
            "Kiara Huynh", "Layton Garner", "Jacqueline Barron", "Dustin Young", "Zoey James", "Jaxson Franklin", "Angela Gallagher", "Marcos Hutchinson", "Jamie Welch", "Hendrix Hurley", 
            "Rylan Austin", "Omar Cantu", "Galilea Chavez", "Ian Cardenas", "Raven Valdez", "Kyler Poole", "Bonnie Bond", "Roger Gould", "Violeta Mayo", "Jericho Davis", 
            "Mia Roy", "Marcelo Haley", "Addilynn Kirk", "Alessandro Landry", "Brynleigh Howe", "Alaric Santana", "Myra Tucker", "Ivan Rowland", "Harleigh Knox", "Valentin Gilbert", 
            "Jocelyn McCarty", "Blaise Brock", "Jada Campos", "Gideon Page", "Cataleya Padilla", "Jaden Porter", "Ryleigh Bowen", "Trevor Roach", "Lyanna Hill", "Isaac Hinton", 
            "Jaelynn Stevens", "Zachary Gaines", "Aya Sierra", "Dayton Ward", "Ariana Lynch", "Zane Soto", "Brynlee Thornton", "Malik Sanford", "Emerald Mosley", "Rayden Yu", 
            "Navy Parrish", "Karsyn Park", "Lia Nielsen", "Tru Nelson", "Everly Rowland", "Eliezer Macdonald", "Rosalia McClure", "Reese Wise", "Mira Greer", "Koda Horne", 
            "Marlowe Shaffer", "Dexter Newman", "Oaklynn Benitez", "Justice Crawford", "Aubree Donaldson", "Canaan Dejesus", "Julissa Whitehead", "Zayd Duke", "Melani Mathis", "Gustavo Chang", 
            "Ophelia Christensen", "Gregory Hardin", "Vada Hogan", "Sonny Stephens", "Millie Velez", "Kareem Carter", "Lucy Frank", "Braylen Trejo", "Rosalyn Avila", "Jaylen Cantrell", 
            "Yamileth Olsen", "Skyler Chapman", "Zuri Lam", "Bodie Tang", "Belle Lugo", "Santos McIntosh", "Gwen Leal", "Cedric Jefferson", "Julieta Knox", "Valentin Kim"
        ]
        random_name = random.choice(names)
        name_with_heart = random_name 
        
        # Use specific client params for profile update
        client_params = self._get_client_params()
        client_params["source_url"] = "https://superlive.chat/profile/edit-profile"
        
        payload = {
            "client_params": client_params,
            "name": name_with_heart,
            "bio": "SDE 🖥️"
        }
        
        return await self._make_request(
            "POST", 
            "/users/update", 
            client, 
            headers=headers, 
            json=payload, 
            error_context="Update profile failed",
            base_url=base_url
        )

    def _get_client_params(self, livestream_id=None):
        source_url = "https://superlive.chat/profile/myprofile"
        if livestream_id:
            source_url = f"https://superlive.chat/livestream/{livestream_id}"
            
        return {
            "os_type": "web",
            "ad_nationality": None,
            "app_build": "3.16.8",
            "app": "superlive",
            "build_code": "639-2941571-prod",
            "app_language": "en",
            "device_language": "en",
            "device_preferred_languages": ["en-US"],
            "source_url": source_url,
            "session_source_url": "https://superlive.chat/discover",
            "referrer": "https://superlive.chat/discover",
            "adid": "466f7443143a3df42868339f73e53887",
            "adjust_attribution_data": {
                "adid": "466f7443143a3df42868339f73e53887",
                "tracker_token": "mii5ej6",
                "tracker_name": "Organic",
                "network": "Organic"
            },
            "adjust_web_uuid": "7db60b38-4a09-44af-82be-ecbbdb651c3e",
            "firebase_analytics_id": "1134312538.1765088771",
            "incognito": True,
            "installation_id": "cbfd66d2-202d-4e61-89c4-3fd6e0986af9",
            "rtc_id": "3455648103",
            "uuid_c1": "PDTmQ51-ZSyxszb4a9Lr2jVJosWRKfgp",
            "vl_cid": None,
            "ttp": "01KBVQTFYEQNYS9BNY68FRVXTV_.tt.1",
            "twclid": None,
            "tdcid": None,
            "fbc": None,
            "fbp": "fb.1.1765088773919.96546003186470457",
            "ga_session_id": "1765088771",
            "web_type": 1
        }

api_viewmodel = ApiViewModel()
