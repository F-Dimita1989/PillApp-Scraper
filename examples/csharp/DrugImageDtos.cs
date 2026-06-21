using System.Text.Json.Serialization;

namespace PillApp.Api.DrugImages;

/// <summary>
/// Payload inviato al microservizio Python.
/// Solo AIC è obbligatorio; name migliora la copertura della ricerca.
/// </summary>
public sealed class DrugInfoRequest
{
    [JsonPropertyName("aic")]
    public required string Aic { get; init; }

    [JsonPropertyName("name")]
    public string? Name { get; init; }
}

/// <summary>
/// Risposta del microservizio Python.
/// </summary>
public sealed class DrugImageResponse
{
    [JsonPropertyName("success")]
    public bool Success { get; init; }

    [JsonPropertyName("imageUrl")]
    public string? ImageUrl { get; init; }

    [JsonPropertyName("sourcePageUrl")]
    public string? SourcePageUrl { get; init; }

    [JsonPropertyName("message")]
    public string Message { get; init; } = "";

    public static DrugImageResponse Unavailable(string message = "Immagine non trovata") =>
        new() { Success = false, Message = message };
}
