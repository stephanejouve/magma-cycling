import Foundation

/// Validation des credentials Intervals.icu.
enum IntervalsValidator {
    enum ValidationError: LocalizedError {
        case authFailed
        case networkError(String)

        var errorDescription: String? {
            switch self {
            case .authFailed:
                return "Connexion echouee -- verifie ton ID et ta cle API."
            case .networkError(let msg):
                return "Erreur reseau: \(msg)"
            }
        }
    }

    /// Valide les credentials et retourne le nom de l'athlete.
    static func validate(athleteID: String, apiKey: String) async throws -> String {
        let urlString = "https://intervals.icu/api/v1/athlete/\(athleteID)"
        guard let url = URL(string: urlString) else {
            throw ValidationError.authFailed
        }

        // Basic auth : "API_KEY:{apiKey}" en base64
        let credentials = "API_KEY:\(apiKey)"
        guard let credData = credentials.data(using: .utf8) else {
            throw ValidationError.authFailed
        }
        let base64 = credData.base64EncodedString()

        var request = URLRequest(url: url)
        request.setValue("Basic \(base64)", forHTTPHeaderField: "Authorization")
        request.timeoutInterval = 10

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await URLSession.shared.data(for: request)
        } catch {
            throw ValidationError.networkError(error.localizedDescription)
        }

        guard let http = response as? HTTPURLResponse else {
            throw ValidationError.networkError("Reponse invalide")
        }

        guard http.statusCode == 200 else {
            throw ValidationError.authFailed
        }

        // Extraire le nom
        if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            if let name = json["name"] as? String, !name.isEmpty {
                return name
            }
            if let athlete = json["athlete"] as? [String: Any],
               let name = athlete["name"] as? String, !name.isEmpty
            {
                return name
            }
        }

        return athleteID
    }
}
