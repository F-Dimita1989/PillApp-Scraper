using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

namespace PillApp.Api.DrugImages;

public sealed class DrugImageServiceOptions
{
    public const string SectionName = "DrugImageService";

    /// <summary>
    /// URL base del microservizio Python su Render.
    /// Es: https://pillapp-drug-image.onrender.com
    /// </summary>
    public string BaseUrl { get; set; } = "";

    public int TimeoutSeconds { get; set; } = 25;
}

public interface IDrugImageService
{
    Task<DrugImageResponse> FetchPackageImageAsync(
        DrugInfoRequest request,
        CancellationToken cancellationToken = default);
}

public sealed class DrugImageService : IDrugImageService
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        PropertyNameCaseInsensitive = true,
    };

    private readonly HttpClient _httpClient;
    private readonly ILogger<DrugImageService> _logger;

    public DrugImageService(HttpClient httpClient, ILogger<DrugImageService> logger)
    {
        _httpClient = httpClient;
        _logger = logger;
    }

    public async Task<DrugImageResponse> FetchPackageImageAsync(
        DrugInfoRequest request,
        CancellationToken cancellationToken = default)
    {
        try
        {
            using var response = await _httpClient.PostAsJsonAsync(
                "/api/v1/drugs/image",
                request,
                JsonOptions,
                cancellationToken);

            if (!response.IsSuccessStatusCode)
            {
                _logger.LogWarning(
                    "Drug image service HTTP {StatusCode} per AIC {Aic}",
                    (int)response.StatusCode,
                    request.Aic);

                return DrugImageResponse.Unavailable(
                    "Servizio immagini temporaneamente non disponibile");
            }

            var result = await response.Content.ReadFromJsonAsync<DrugImageResponse>(
                JsonOptions,
                cancellationToken);

            return result ?? DrugImageResponse.Unavailable();
        }
        catch (TaskCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            _logger.LogWarning("Timeout drug image service per AIC {Aic}", request.Aic);
            return DrugImageResponse.Unavailable("Timeout recupero immagine");
        }
        catch (HttpRequestException ex)
        {
            _logger.LogError(ex, "Errore rete verso drug image service");
            return DrugImageResponse.Unavailable("Servizio immagini non raggiungibile");
        }
    }
}

public static class DrugImageServiceExtensions
{
    public static IServiceCollection AddDrugImageService(
        this IServiceCollection services,
        IConfiguration configuration)
    {
        services.Configure<DrugImageServiceOptions>(
            configuration.GetSection(DrugImageServiceOptions.SectionName));

        services.AddHttpClient<IDrugImageService, DrugImageService>((sp, client) =>
        {
            var options = sp.GetRequiredService<
                IOptions<DrugImageServiceOptions>>().Value;

            if (string.IsNullOrWhiteSpace(options.BaseUrl))
                throw new InvalidOperationException(
                    "DrugImageService:BaseUrl non configurato");

            client.BaseAddress = new Uri(options.BaseUrl.TrimEnd('/') + "/");
            client.Timeout = TimeSpan.FromSeconds(options.TimeoutSeconds);
            client.DefaultRequestHeaders.Add("Accept", "application/json");
        });

        return services;
    }
}
