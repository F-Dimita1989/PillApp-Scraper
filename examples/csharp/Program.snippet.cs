// Aggiungi in Program.cs del backend C# PillApp su Render:

using PillApp.Api.DrugImages;

var builder = WebApplication.CreateBuilder(args);

// ... servizi esistenti ...
builder.Services.AddDrugImageService(builder.Configuration);

var app = builder.Build();

// ... middleware esistenti ...
app.MapControllers();
app.Run();
