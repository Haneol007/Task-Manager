using Prayerify.ViewModels;

namespace Prayerify.Pages
{
	public partial class CategoriesPage : ContentPage
	{
		private readonly CategoriesViewModel _viewModel;

		public CategoriesPage(CategoriesViewModel viewModel)
		{
			InitializeComponent();
			BindingContext = _viewModel = viewModel;
		}

		protected override async void OnAppearing()
		{
			base.OnAppearing();
			await _viewModel.LoadAsync();
		}
	}
}


