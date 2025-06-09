// Sample Scala file for testing API detection
import akka.http.scaladsl.Http
import akka.http.scaladsl.client.RequestBuilding._
import play.api.libs.ws._
import sttp.client3._
import scalaj.http._
import requests._

object ApiTestSample {
  implicit val system = ActorSystem()
  implicit val materializer = ActorMaterializer()
  
  // Akka HTTP examples
  val akkaGet = Http().singleRequest(Get("https://api.github.com/users/octocat"))
  val akkaPost = Http().singleRequest(Post("https://api.example.com/users", """{"name": "John"}"""))
  
  // Play WS examples  
  def playWsExample(ws: WSClient) = {
    val getResponse = ws.url("https://jsonplaceholder.typicode.com/posts/1").get()
    val postResponse = ws.url("https://jsonplaceholder.typicode.com/posts")
      .withHeaders("Content-Type" -> "application/json")
      .post("""{"title": "New Post", "body": "Content", "userId": 1}""")
  }
  
  // STTP examples
  val backend = HttpURLConnectionBackend()
  val sttpGet = basicRequest
    .get(uri"https://httpbin.org/get")
    .auth.bearer("token123")
    .send(backend)
    
  val sttpPost = basicRequest
    .post(uri"https://httpbin.org/post")
    .body("""{"data": "test"}""")
    .send(backend)
  
  // ScalaJ HTTP examples
  val scalajGet = Http("https://api.coindesk.com/v1/bpi/currentprice.json").asString
  val scalajPost = Http("https://httpbin.org/post")
    .postForm(Seq("key1" -> "value1", "key2" -> "value2"))
    .asString
    
  // Requests-scala examples
  val requestsGet = requests.get("https://api.ipify.org?format=json")
  val requestsPost = requests.post("https://httpbin.org/post", data = """{"test": "data"}""")
  
  // Java HTTP Client examples
  import java.net.http.HttpClient
  import java.net.http.HttpRequest
  import java.net.http.HttpResponse
  import java.time.Duration
  
  // Basic HttpClient with GET
  val client = HttpClient.newHttpClient()
  val getRequest = HttpRequest.newBuilder()
    .uri(java.net.URI.create("https://api.example.com/data"))
    .GET()
    .build()
  
  // HttpClient with custom configuration
  val customClient = HttpClient.newBuilder()
    .connectTimeout(Duration.ofSeconds(20))
    .build()
  
  // POST request with JSON body
  val postRequest = HttpRequest.newBuilder()
    .uri(java.net.URI.create("https://api.example.com/users"))
    .header("Content-Type", "application/json")
    .header("Authorization", "Bearer token123")
    .POST(HttpRequest.BodyPublishers.ofString("""{"name": "John", "email": "john@example.com"}"""))
    .build()
  
  // POST request with form data
  val formData = "username=admin&password=secret&remember=true"
  val formPostRequest = HttpRequest.newBuilder()
    .uri(java.net.URI.create("https://api.example.com/login"))
    .header("Content-Type", "application/x-www-form-urlencoded")
    .POST(HttpRequest.BodyPublishers.ofString(formData))
    .build()
  
  // PUT request with timeout
  val putRequest = HttpRequest.newBuilder()
    .uri(java.net.URI.create("https://api.example.com/users/123"))
    .header("Content-Type", "application/json")
    .timeout(Duration.ofMinutes(2))
    .PUT(HttpRequest.BodyPublishers.ofString("""{"name": "Updated Name"}"""))
    .build()
  
  // DELETE request
  val deleteRequest = HttpRequest.newBuilder()
    .uri(java.net.URI.create("https://api.example.com/users/123"))
    .header("Authorization", "Basic dXNlcjpwYXNzd29yZA==")
    .DELETE()
    .build()
  
  // PATCH request with file upload simulation
  val patchRequest = HttpRequest.newBuilder()
    .uri(java.net.URI.create("https://api.example.com/files/upload"))
    .header("Content-Type", "multipart/form-data")
    .method("PATCH", HttpRequest.BodyPublishers.ofString("file content here"))
    .build()
  
  // Execute requests (examples)
  val getResponse = client.send(getRequest, HttpResponse.BodyHandlers.ofString())
  val postResponse = customClient.send(postRequest, HttpResponse.BodyHandlers.ofString())
}