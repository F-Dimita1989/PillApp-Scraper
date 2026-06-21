using System.Text.Json.Serialization;

namespace PillApp.Api.DrugImages;

/// <summary>
/// Payload inviato al microservizio Python (snake_case).
/// </summary>
public sealed class DrugInfoRequest
{
    [JsonPropertyName("aic")]
    public required string Aic { get; init; }

    [JsonPropertyName("name")]
    public required string Name { get; init; }

    [JsonPropertyName("dosage")]
    public string? Dosage { get; init; }

    [JsonPropertyName("pharmaceutical_form")]
    public string? PharmaceuticalForm { get; init; }

    [JsonPropertyName("package_quantity")]
    public string? PackageQuantity { get; init; }

    [JsonPropertyName("marketing_authorization_holder")]
    public string? MarketingAuthorizationHolder { get; init; }
}

/// <summary>
/// Risposta del microservizio Python — stesso contratto usato da React Native.
/// </summary>
public sealed class DrugImageResponse
{
    [JsonPropertyName("success")]
    public bool Success { get; init; }

    [JsonPropertyName("imageUrl")]
    public string? ImageUrl { get; init; }

    [JsonPropertyName("sourcePageUrl")]
    public string? SourcePageUrl { get; init; }

    [JsonPropertyName("confidenceScore")]
    public double ConfidenceScore { get; init; }

    [JsonPropertyName("matchedFields")]
    public IReadOnlyList<string> MatchedFields { get; init; } = [];

    [JsonPropertyName("rejectedReasons")]
    public IReadOnlyList<string> RejectedReasons { get; init; } = [];

    [JsonPropertyName("message")]
    public string Message { get; init; } = "";

    public static DrugImageResponse Unavailable(string message = "Immagine non trovata in modo affidabile") =>
        new()
        {
            Success = false,
            Message = message,
        };
}
